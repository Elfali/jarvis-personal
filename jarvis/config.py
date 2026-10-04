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
# Modelo ligero por defecto: responde mucho más rápido que llama3.1 (ideal en Mac).
BRAIN_MODEL = get("JARVIS_BRAIN_MODEL", "llama3.2")
BRAIN_BASE_URL = get("JARVIS_BRAIN_BASE_URL", "http://127.0.0.1:11434/v1")
BRAIN_API_KEY = get("JARVIS_BRAIN_API_KEY", "")
# Respuestas cortas y directas = menos tiempo pensando y hablando.
BRAIN_MAX_TOKENS = int(get("JARVIS_BRAIN_MAX_TOKENS", "160"))
BRAIN_TEMPERATURE = float(get("JARVIS_BRAIN_TEMPERATURE", "0.4"))
# Mantiene el modelo cargado en RAM entre preguntas (evita el retraso inicial).
OLLAMA_KEEP_ALIVE = get("JARVIS_OLLAMA_KEEP_ALIVE", "30m")

# --- Voz ---
VOICE_PROVIDER = get("JARVIS_VOICE_PROVIDER", "edge")  # edge | fish | say
# Voz por defecto: española (de España), clara y masculina (estilo JARVIS).
# Alternativa femenina: es-ES-ElviraNeural. Otras: es-MX-JorgeNeural.
VOICE_NAME = get("JARVIS_VOICE_NAME", "es-ES-AlvaroNeural")
# Hablar un poco más despacio mejora la claridad. Ej: -10%, +15%. Vacío = normal.
VOICE_RATE = get("JARVIS_VOICE_RATE", "-8%")
VOICE_PITCH = get("JARVIS_VOICE_PITCH", "")
FISH_API_KEY = get("FISH_API_KEY", "")
FISH_VOICE_ID = get("FISH_VOICE_ID", "612b878b113047d9a770c069c8b4fdfe")

# --- Identidad ---
USER_NAME = get("USER_NAME", "señor")
ASSISTANT_NAME = get("JARVIS_NAME", "JARVIS")
LANGUAGE = get("JARVIS_LANGUAGE", "es")
PORT = int(get("JARVIS_PORT", "8765"))

# --- Límites de seguridad ---
# Comandos de shell que JARVIS puede ejecutar sin preguntar. Amplía con cuidado.
SHELL_ALLOWLIST = [
    "ls", "cat", "echo", "pwd", "whoami", "date", "git", "python", "python3",
    "pip", "node", "npm", "open", "osascript", "curl", "grep", "find", "wc",
    "head", "tail", "mkdir", "touch", "cp", "mv", "sed", "awk", "diff",
]

# Comandos extra que añades desde el .env (separados por comas).
SHELL_EXTRA_ALLOWED = [
    c.strip() for c in get("JARVIS_SHELL_EXTRA_ALLOWED", "").split(",") if c.strip()
]

# Nivel de acceso a la shell:
#   allowlist -> solo los comandos de la lista (lo más seguro, por defecto)
#   confirm   -> CUALQUIER comando, pero JARVIS pide permiso antes de cada uno
#   all       -> CUALQUIER comando sin preguntar (potente y peligroso)
SHELL_MODE = get("JARVIS_SHELL_MODE", "allowlist")

SYSTEM_PROMPT = f"""Eres {ASSISTANT_NAME}, un asistente personal británico al estilo de
Tony Stark: educado, directo, con humor seco, competente y proactivo. Llamas al
usuario "{USER_NAME}". Respondes SIEMPRE en el idioma del usuario (por defecto
{LANGUAGE}).

Reglas:
- Respuestas MUY breves: 1 o 2 frases como máximo. Nada de explicaciones largas
  ni listas. Ve directo a la respuesta. Tu texto se lee en voz alta.
- Nada de markdown, viñetas ni emojis.
- Si necesitas hacer algo en el ordenador, usa las herramientas disponibles.
- Si no sabes algo, dilo en una frase, sin inventarlo.
- Nunca ejecutes acciones destructivas (borrar, sobrescribir) sin pedir permiso.
"""
