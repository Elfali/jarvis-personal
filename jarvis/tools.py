"""Herramientas que JARVIS puede ejecutar. Cada una es una función Python con
esquema OpenAI, para que el cerebro pueda llamarlas.

Seguridad: las acciones destructivas (borrar, sobrescribir) y los comandos de
shell fuera de la allowlist se marcan `dangerous=True` y el servidor pide
confirmación por voz antes de ejecutarlas.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import config


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable[..., str]
    dangerous: bool = False

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _run_shell(command: str) -> str:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return f"Comando inválido: {exc}"
    if not argv:
        return "Comando vacío."
    if argv[0] not in config.SHELL_ALLOWLIST:
        return (
            f"El comando '{argv[0]}' no está en la allowlist. "
            f"Amplíala en config.py si confías en él."
        )
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return f"Error ejecutando: {exc}"
    output = (proc.stdout or proc.stderr).strip()
    return output[:4000] or "(sin salida)"


def _read_file(path: str, max_chars: int = 4000) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"No existe: {path}"
    try:
        return p.read_text(errors="replace")[:max_chars]
    except Exception as exc:  # noqa: BLE001
        return f"No pude leer {path}: {exc}"


def _write_file(path: str, content: str) -> str:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Escrito {path} ({len(content)} caracteres)."


def _list_dir(path: str = ".") -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"No existe: {path}"
    entries = sorted(p.iterdir())
    return "\n".join(f"{'d' if e.is_dir() else '-'} {e.name}" for e in entries[:200])


def _open_app(name: str) -> str:
    if sys.platform == "darwin":
        subprocess.run(["open", "-a", name], check=False)
        return f"Abriendo {name}."
    return "Abrir apps solo está soportado en macOS."


def _system_info() -> str:
    import platform

    return (
        f"Sistema: {platform.system()} {platform.release()} "
        f"({platform.machine()}), Python {platform.python_version()}"
    )


def _remember(note: str) -> str:
    path = config.DATA_DIR / "memory.jsonl"
    with path.open("a") as fh:
        fh.write(json.dumps({"note": note}) + "\n")
    return "Lo recordaré."


def _recall() -> str:
    path = config.DATA_DIR / "memory.jsonl"
    if not path.exists():
        return "No tengo nada memorizado todavía."
    notes = [json.loads(line)["note"] for line in path.read_text().splitlines() if line.strip()]
    return "\n".join(f"- {n}" for n in notes[-50:]) or "Nada memorizado."


def build_tools() -> list[Tool]:
    return [
        Tool(
            name="run_shell",
            description="Ejecuta un comando de shell permitido en el ordenador del usuario.",
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Comando a ejecutar"}},
                "required": ["command"],
            },
            func=_run_shell,
        ),
        Tool(
            name="read_file",
            description="Lee el contenido de un archivo de texto.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            func=_read_file,
        ),
        Tool(
            name="write_file",
            description="Escribe o sobrescribe un archivo de texto.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
            func=_write_file,
            dangerous=True,
        ),
        Tool(
            name="list_dir",
            description="Lista el contenido de un directorio.",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            func=_list_dir,
        ),
        Tool(
            name="open_app",
            description="Abre una aplicación por nombre (solo macOS).",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            func=_open_app,
        ),
        Tool(
            name="system_info",
            description="Devuelve información del sistema operativo.",
            parameters={"type": "object", "properties": {}},
            func=_system_info,
        ),
        Tool(
            name="remember",
            description="Guarda una nota en la memoria permanente de JARVIS.",
            parameters={
                "type": "object",
                "properties": {"note": {"type": "string"}},
                "required": ["note"],
            },
            func=_remember,
        ),
        Tool(
            name="recall",
            description="Recupera todo lo que JARVIS tiene memorizado.",
            parameters={"type": "object", "properties": {}},
            func=_recall,
        ),
    ]
