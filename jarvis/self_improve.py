"""Auto-mejora: JARVIS edita su propio código cuando se lo ordenas.

Flujo:
  1. Se le da el cerebro un "brief" con la estructura del proyecto.
  2. El cerebro propone los archivos a escribir (JSON).
  3. Se hace copia de seguridad del original, se aplica el cambio, y se prueba
     que los módulos siguen importando.
  4. Si algo se rompe, se revierte automáticamente.

Así "mejórate a ti mismo" es seguro: siempre hay vuelta atrás.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import config
from .brain import Brain, BrainError

PROJECT_ROOT = config.ROOT
SELF_DIR = PROJECT_ROOT / "jarvis"
BACKUP_DIR = config.DATA_DIR / "backups"

SELF_PROMPT = """Eres el módulo de auto-mejora de JARVIS. El usuario te ha pedido
un cambio en tu propio código fuente. Debes responder SOLO con un objeto JSON:

{"summary": "qué cambiaste y por qué", "files": {"ruta/relativa.py": "contenido COMPLETO nuevo"}}

Reglas:
- Las rutas son relativas a la raíz del proyecto.
- Incluye el archivo ENTERO, no un diff.
- Cambios pequeños y verificables. No rompas la interfaz pública de los módulos.
- No añadas dependencias nuevas salvo que sea imprescindible.
"""


def _project_tree() -> str:
    lines = []
    for path in sorted(PROJECT_ROOT.rglob("*.py")):
        if "data" in path.parts or "__pycache__" in path.parts:
            continue
        lines.append(str(path.relative_to(PROJECT_ROOT)))
    return "\n".join(lines)


def _import_check() -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-c", "import jarvis.brain, jarvis.voice, jarvis.tools, jarvis.agent"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def _backup(paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / stamp
    dest.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            rel = path.relative_to(PROJECT_ROOT)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return dest


def _restore(backup: Path) -> None:
    for src in backup.rglob("*"):
        if src.is_file():
            rel = src.relative_to(backup)
            shutil.copy2(src, PROJECT_ROOT / rel)


def improve(request: str, brain: Brain) -> str:
    """Aplica una mejora pedida por el usuario. Devuelve un resumen hablado."""
    brief = (
        f"{SELF_PROMPT}\n\n"
        f"Archivos actuales del proyecto:\n{_project_tree()}\n\n"
        f"Contenido relevante que puedes necesitar está en esos archivos.\n\n"
        f"Petición del usuario: {request}"
    )
    messages = [
        {"role": "system", "content": "Responde únicamente con JSON válido."},
        {"role": "user", "content": brief},
    ]
    try:
        reply = brain.chat(messages)
    except BrainError as exc:
        return f"No pude pensar la mejora: {exc}"

    raw = reply.get("content", "").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        raw = raw[4:] if raw.startswith("json") else raw
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        return "El cerebro no devolvió un plan de mejora válido; no toqué nada."

    files: dict = plan.get("files", {})
    if not files:
        return "El cerebro no propuso cambios."

    targets = [PROJECT_ROOT / rel for rel in files]
    backup = _backup(targets)
    try:
        for rel, content in files.items():
            path = PROJECT_ROOT / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        ok, err = _import_check()
        if not ok:
            _restore(backup)
            return f"La mejora rompió el código y la revertí. Error: {err[:200]}"
    except Exception as exc:  # noqa: BLE001
        _restore(backup)
        return f"Falló la mejora y la revertí: {exc}"

    return plan.get("summary", "Mejora aplicada.") + " (copia de seguridad guardada)"
