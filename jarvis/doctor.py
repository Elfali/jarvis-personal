"""Diagnóstico de JARVIS: comprueba cerebro y voz y explica cómo arreglarlo.

Uso:  python -m jarvis.doctor      (o ./doctor.sh)
"""

from __future__ import annotations

import shutil
import subprocess

from . import config, voice
from .brain import Brain

OK = "✅"
BAD = "❌"
WARN = "⚠️ "


def check_brain() -> bool:
    brain = Brain()
    print(f"\n🧠 Cerebro: {brain.provider}  (modelo: {brain.model})")
    if brain.provider == "claude_code":
        if shutil.which("claude"):
            print(f"{OK} CLI `claude` encontrado")
            return True
        print(f"{BAD} El CLI `claude` no está instalado.")
        print("   Instálalo con:  npm install -g @anthropic-ai/claude-code")
        return False

    ok, msg = brain.health()
    if ok:
        print(f"{OK} {msg}")
        return True

    print(f"{BAD} {msg}")
    if brain.provider == "ollama":
        print("   Ollama no está corriendo. Arréglalo así:")
        print("     1) brew install --cask ollama")
        print("     2) Abre la app Ollama (o: ollama serve)")
        print(f"     3) ollama pull {brain.model}")
        print("   Alternativa sin Ollama: usa una API gratuita (ver README, sección 'Elegir el cerebro').")
    return False


def check_voice() -> bool:
    print(f"\n🗣️  Voz: {config.VOICE_PROVIDER}  (voz: {config.VOICE_NAME})")
    try:
        audio, mime = voice.speak("Buenas tardes, señor. Prueba de voz.")
    except Exception as exc:  # noqa: BLE001
        print(f"{BAD} No se pudo generar voz: {exc}")
        return False
    print(f"{OK} Voz generada: {len(audio)} bytes ({mime})")
    if config.VOICE_NAME.startswith("en-") and config.LANGUAGE == "es":
        print(f"{WARN}La voz es inglesa pero JARVIS habla en español: sonará mal.")
        print("   En .env pon:  JARVIS_VOICE_NAME=es-ES-AlvaroNeural")
    print("   (en macOS puedes oírla con:  ./say-test.sh)")
    return True


def main() -> None:
    print("=" * 56)
    print("  Diagnóstico de JARVIS")
    print("=" * 56)
    brain_ok = check_brain()
    voice_ok = check_voice()
    print("\n" + "=" * 56)
    if brain_ok and voice_ok:
        print(f"{OK} Todo listo. Arranca con:  ./start.sh")
    else:
        print(f"{WARN}Revisa los puntos marcados con {BAD} arriba.")
    print("=" * 56)


if __name__ == "__main__":
    main()
