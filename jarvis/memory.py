"""Memoria persistente de JARVIS, guardada en disco (en el servidor).

Todo vive en DATA_DIR, de modo que en un servidor basta con montar esa carpeta
como volumen para que la memoria sobreviva a reinicios y actualizaciones.

Dos ficheros JSONL:
  - memory.jsonl   -> hechos duraderos que JARVIS decide recordar.
  - history.jsonl  -> registro completo de la conversación (nada se pierde).

JSONL (una línea = un objeto) es robusto: si un apagado corta una escritura,
solo se pierde la última línea, nunca el fichero entero.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import config

MEMORY_FILE = "memory.jsonl"
HISTORY_FILE = "history.jsonl"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _append(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _memory_path() -> Path:
    return config.DATA_DIR / MEMORY_FILE


def _history_path() -> Path:
    return config.DATA_DIR / HISTORY_FILE


# --- Hechos duraderos ---


def remember(note: str) -> str:
    note = (note or "").strip()
    if not note:
        return "No hay nada que recordar."
    _append(_memory_path(), {"t": _now(), "note": note})
    return "Lo recordaré."


def recall(query: str = "", limit: int = 50) -> str:
    notes = _read(_memory_path())
    if query:
        q = query.lower()
        notes = [n for n in notes if q in str(n.get("note", "")).lower()]
    if not notes:
        return (
            "No tengo nada memorizado sobre eso."
            if query
            else "No tengo nada memorizado todavía."
        )
    return "\n".join(f"- {n.get('note', '')}" for n in notes[-limit:])


# --- Registro de la conversación ---


def save_turn(user: str, assistant: str) -> None:
    _append(_history_path(), {"t": _now(), "user": user, "assistant": assistant})


def history(limit: int = 20) -> list[dict]:
    return _read(_history_path())[-limit:]


def stats() -> dict:
    return {
        "notas": len(_read(_memory_path())),
        "turnos": len(_read(_history_path())),
        "carpeta": str(config.DATA_DIR),
    }


# --- Aprendizaje automático (opcional) ---

_EXTRACT_PROMPT = (
    "Extrae de este intercambio SOLO hechos duraderos y útiles sobre el usuario "
    "(preferencias, datos personales, proyectos, rutinas). Devuelve una lista "
    "JSON de frases cortas en español. Si no hay nada digno de recordar, "
    "devuelve []."
)


def extract_facts(brain, user: str, assistant: str) -> list[str]:
    """Pide al cerebro que saque hechos duraderos del último intercambio.

    Es opcional y puede costar una llamada extra al modelo. Si algo falla,
    devuelve lista vacía sin romper la conversación.
    """
    messages = [
        {"role": "system", "content": _EXTRACT_PROMPT},
        {"role": "user", "content": f"Usuario: {user}\nJARVIS: {assistant}"},
    ]
    try:
        reply = brain.chat(messages)
        raw = (reply.get("content") or "").strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        facts = json.loads(raw)
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(facts, list):
        return []
    limpios = [str(f).strip() for f in facts if str(f).strip()]
    for fact in limpios:
        remember(fact)
    return limpios
