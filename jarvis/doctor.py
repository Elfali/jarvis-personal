"""Diagnóstico de JARVIS: comprueba cerebro y voz y explica cómo arreglarlo.

Uso:  python -m jarvis.doctor      (o ./doctor.sh)
"""

from __future__ import annotations

import shutil

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

    if brain.provider == "ollama":
        if shutil.which("ollama"):
            print(f"{OK} El comando `ollama` está instalado")
        else:
            print(f"{BAD} Ollama no está instalado.")
            print("   Instálalo con:  ./setup-brain.sh")
            return False

    ok, msg = brain.health()
    if not ok:
        print(f"{BAD} {msg}")
        if brain.provider == "ollama":
            print("   Arréglalo con:  ./setup-brain.sh")
        return False
    print(f"{OK} {msg}")

    # Prueba real: pedir una respuesta de verdad (no solo ver el servidor).
    try:
        reply = brain.chat([{"role": "user", "content": "Di solo: ok"}])
        text = (reply.get("content") or "").strip()
        print(f"{OK} El cerebro respondió: {text[:60]!r}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"{BAD} El cerebro no dio respuesta: {exc}")
        if brain.provider == "ollama":
            print(f"   ¿Falta el modelo?  ollama pull {brain.model}")
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
    print("   Para oírla en los altavoces:  ./say-test.sh")
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
        print("   ¿Cerebro en rojo? Ejecuta:  ./setup-brain.sh")
    print("=" * 56)


if __name__ == "__main__":
    main()
