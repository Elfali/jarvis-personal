"""El bucle del agente: conversación + llamada a herramientas hasta responder.

`respond()` recibe la historia de la conversación y devuelve (texto, audio_mime,
audio_bytes). Ejecuta las herramientas que el cerebro pida, con confirmación
para las peligrosas.
"""

from __future__ import annotations

from . import config, voice
from .brain import Brain, BrainError, tool_call_name_and_args
from .tools import build_tools


class Agent:
    def __init__(self) -> None:
        self.brain = Brain()
        self.tools = {t.name: t for t in build_tools()}
        self.schemas = [t.schema() for t in self.tools.values()]

    def _system(self) -> dict:
        return {"role": "system", "content": config.SYSTEM_PROMPT}

    @staticmethod
    def _trim(history: list[dict]) -> list[dict]:
        """Recorta el historial a los últimos turnos.

        Menos historial = el modelo piensa antes y se centra en lo relevante.
        Se corta solo por turnos de usuario, para no partir una llamada a
        herramienta de su resultado.
        """
        limit = config.HISTORY_MAX_TURNS
        if limit <= 0 or len(history) <= limit:
            return history
        return history[-limit:]

    def respond(self, history: list[dict], confirm=None) -> tuple[str, str | None, bytes | None]:
        """history: lista de {role, content}. Devuelve (texto, mime, audio).

        `confirm(tool_name, args) -> bool` se llama antes de una herramienta
        peligrosa. Si es None, se rechazan las peligrosas.
        """
        messages = [self._system(), *self._trim(history)]

        for _ in range(config.TOOL_ROUNDS):
            try:
                reply = self.brain.chat(messages, tools=self.schemas)
            except BrainError as exc:
                text = f"Lo siento, {config.USER_NAME}. Mi cerebro no responde: {exc}"
                return self._with_voice(text)

            tool_calls = reply.get("tool_calls") or []
            if not tool_calls:
                text = (reply.get("content") or "").strip() or "No tengo nada que decir."
                return self._with_voice(text)

            messages.append(reply)
            for call in tool_calls:
                name, args = tool_call_name_and_args(call)
                result = self._execute(name, args, confirm)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id", ""),
                        "content": result,
                    }
                )

        text = "Me he liado con demasiadas herramientas; dime otra vez qué querías."
        return self._with_voice(text)

    def _execute(self, name: str, args: dict, confirm) -> str:
        tool = self.tools.get(name)
        if tool is None:
            return f"Herramienta desconocida: {name}"
        if tool.needs_confirmation(args):
            if confirm is None or not confirm(name, args):
                return "El usuario no autorizó esa acción."
        try:
            return str(tool.func(**args))
        except Exception as exc:  # noqa: BLE001
            return f"La herramienta {name} falló: {exc}"

    def _with_voice(self, text: str) -> tuple[str, str | None, bytes | None]:
        try:
            audio, mime = voice.speak(text)
            return text, mime, audio
        except Exception:  # noqa: BLE001
            return text, None, None
