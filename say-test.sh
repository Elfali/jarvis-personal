#!/usr/bin/env bash
# Reproduce por los altavoces una frase de prueba con la voz configurada (macOS).
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate
python - <<'PY'
from jarvis import voice, config
texto = "Buenas tardes, señor. Soy JARVIS. Todos los sistemas funcionan correctamente."
audio, mime = voice.speak(texto)
ext = "mp3" if "mpeg" in mime else ("aiff" if "aiff" in mime else "wav")
path = f"/tmp/jarvis_voz_prueba.{ext}"
open(path, "wb").write(audio)
print("Voz:", config.VOICE_NAME, "->", path)
PY
open /tmp/jarvis_voz_prueba.mp3 2>/dev/null || open /tmp/jarvis_voz_prueba.aiff
