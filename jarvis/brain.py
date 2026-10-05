"""El cerebro de JARVIS: capa fina sobre el LLM elegido.

Soporta tres proveedores con la misma interfaz:
  - ollama:      modelo local, gratis y privado (endpoint OpenAI-compatible).
  - openai:      cualquier endpoint OpenAI-compatible (OpenAI, Groq, Gemini,
                 OpenRouter, LM Studio...). Cambia base_url + api_key.
  - claude_code: el proceso `claude -p` del JARVIS original (suscripción Claude).

Todos exponen `chat(messages, tools)` devolviendo un mensaje estilo OpenAI, de
modo que el bucle de agente de agent.py no sabe cuál está detrás.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

import httpx

from . import config


class BrainError(RuntimeError):
    pass


class Brain:
    def __init__(self) -> None:
        self.provider = config.BRAIN_PROVIDER
        self.model = config.BRAIN_MODEL
        self.base_url = config.BRAIN_BASE_URL.rstrip("/")
        self.api_key = config.BRAIN_API_KEY

    # --- API pública ---

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        if self.provider == "claude_code":
            return self._chat_claude_code(messages)
        return self._chat_openai(messages, tools)

    def health(self) -> tuple[bool, str]:
        """Comprueba que el cerebro responde. Devuelve (ok, mensaje)."""
        try:
            if self.provider == "claude_code":
                if not shutil.which("claude"):
                    return False, "el CLI `claude` no está instalado o no está en PATH"
                return True, "claude_code listo"
            resp = httpx.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=5.0,
            )
            if resp.status_code >= 500:
                return False, f"{self.provider} devolvió HTTP {resp.status_code}"
            if self.provider == "ollama":
                return self._health_ollama(resp)
            return True, f"{self.provider} responde en {self.base_url}"
        except Exception as exc:  # noqa: BLE001
            return False, f"no se pudo alcanzar el cerebro ({self.provider}): {exc}"

    def _health_ollama(self, models_resp) -> tuple[bool, str]:
        """En Ollama, que el servidor responda no basta: el modelo debe estar
        descargado. Si no lo está, avisamos con la orden exacta para traerlo."""
        api_base = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        try:
            tags = httpx.get(f"{api_base}/api/tags", timeout=5.0).json()
        except Exception:  # noqa: BLE001
            return True, f"ollama responde en {self.base_url}"
        names = {m.get("name", "") for m in tags.get("models", [])}
        if not names:
            return False, (
                f"ollama está corriendo pero no tiene ningún modelo. "
                f"Ejecuta:  ollama pull {self.model}"
            )
        # Coincide "llama3.1" con "llama3.1:latest"
        if self.model not in names and not any(n.split(":")[0] == self.model for n in names):
            disponibles = ", ".join(sorted(names))
            return False, (
                f"el modelo '{self.model}' no está descargado (tienes: {disponibles}). "
                f"Ejecuta:  ollama pull {self.model}"
            )
        return True, f"ollama listo con '{self.model}' en {api_base}"

    # --- Implementaciones ---

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _chat_openai(self, messages: list[dict], tools: list[dict] | None) -> dict:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": config.BRAIN_TEMPERATURE,
            "max_tokens": config.BRAIN_MAX_TOKENS,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        # Mantiene el modelo cargado en memoria (evita el retraso de recarga).
        if self.provider == "ollama":
            payload["keep_alive"] = config.OLLAMA_KEEP_ALIVE
            if config.BRAIN_NUM_CTX > 0:
                payload["num_ctx"] = config.BRAIN_NUM_CTX
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=120.0,
            )
        except Exception as exc:  # noqa: BLE001
            raise BrainError(
                f"No pude hablar con el cerebro en {self.base_url}. "
                f"¿Está Ollama corriendo? ({exc})"
            ) from exc
        if resp.status_code >= 400:
            raise BrainError(f"El cerebro devolvió HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()["choices"][0]["message"]

    def _chat_claude_code(self, messages: list[dict]) -> dict:
        """Ejecuta `claude -p` con la conversación aplanada como prompt."""
        prompt = self._flatten(messages)
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError as exc:
            raise BrainError("El CLI `claude` no está instalado.") from exc
        except subprocess.TimeoutExpired as exc:
            raise BrainError("Claude Code tardó demasiado en responder.") from exc
        if proc.returncode != 0:
            raise BrainError(f"Claude Code falló: {proc.stderr.strip()[:300]}")
        return {"role": "assistant", "content": proc.stdout.strip()}

    @staticmethod
    def _flatten(messages: list[dict]) -> str:
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content") or ""
            if role == "system":
                parts.append(f"[Sistema]\n{content}")
            elif role == "assistant":
                parts.append(f"[Tú]\n{content}")
            else:
                parts.append(f"[Usuario]\n{content}")
        return "\n\n".join(parts)


def tool_call_name_and_args(call: dict) -> tuple[str, dict]:
    """Extrae (nombre, argumentos) de una tool_call estilo OpenAI."""
    fn = call.get("function", {})
    name = fn.get("name", "")
    raw = fn.get("arguments", "{}")
    try:
        args = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except json.JSONDecodeError:
        args = {}
    return name, args
