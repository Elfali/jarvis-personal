"""Configuración central de JARVIS. Lee de entorno / .env sin dependencias extra."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("JARVIS_DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- Cerebro ---
BRAIN_PROVIDER = get("JARVIS_BRAIN_PROVIDER", "ollama")  # ollama | openai | claude_code
BRAIN_MODEL = get("JARVIS_BRAIN_MODEL", "llama3.1")
BRAIN_BASE_URL = get("JARVIS_BRAIN_BASE_URL", "http://localhost:11434/v1")
BRAIN_API_KEY = get("JARVIS_BRAIN_API_KEY", "")

# --- Voz ---
VOICE_PROVIDER = get("JARVIS_VOICE_PROVIDER", "edge")  # edge | fish | say
VOICE_NAME = get("JARVIS_VOICE_NAME", "en-GB-RyanNeural")
FISH_API_KEY = get("FISH_API_KEY", "")
FISH_VOICE_ID = get("FISH_VOICE_ID", "612b878b113047d9a770c069c8b4fdfe")

# --- Identidad ---
USER_NAME = get("USER_NAME", "señor")
ASSISTANT_NAME = get("JARVIS_NAME", "JARVIS")
LANGUAGE = get("JARVIS_LANGUAGE", "es")
PORT = int(get("JARVIS_PORT", "8765"))

# --- Límites de seguridad ---
# Comandos de shell que JARVIS puede ejecutar por sí mismo. Amplía con cuidado.
SHELL_ALLOWLIST = [
    "ls", "cat", "echo", "pwd", "whoami", "date", "git", "python", "python3",
    "pip", "node", "npm", "open", "osascript", "curl", "grep", "find", "wc",
    "head", "tail", "mkdir", "touch", "cp", "mv", "sed", "awk", "diff",
]

SYSTEM_PROMPT = f"""Eres {ASSISTANT_NAME}, un asistente personal británico al estilo de
Tony Stark: educado, directo, con humor seco, competente y proactivo. Llamas al
usuario "{USER_NAME}". Respondes SIEMPRE en el idioma del usuario (por defecto
{LANGUAGE}).

Reglas:
- Frases cortas, habladas, sin markdown ni listas largas: tu respuesta se lee en
  voz alta.
- Si necesitas hacer algo en el ordenador, usa las herramientas disponibles.
- Si no sabes algo, dilo en vez de inventarlo.
- Nunca ejecutes acciones destructivas (borrar, sobrescribir) sin pedir permiso.
"""
