"""La voz de JARVIS. Tres proveedores intercambiables.

  - edge:  Microsoft Edge neural voices vía `edge-tts`. Gratis, sin clave, y la
           voz británica `en-GB-RyanNeural` suena muy cerca del JARVIS original.
  - fish:  Fish Audio, el proveedor del JARVIS original. Requiere FISH_API_KEY
           y usa el mismo voice id del proyecto original.
  - say:   el `say` de macOS. Sin dependencias, siempre disponible como último
           recurso.

`speak(text)` devuelve bytes de audio (mp3/wav/aiff) o lanza VoiceError.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

from . import config


class VoiceError(RuntimeError):
    pass


async def _edge_bytes(text: str) -> bytes:
    import edge_tts

    kwargs = {}
    if config.VOICE_RATE:
        kwargs["rate"] = config.VOICE_RATE
    if config.VOICE_PITCH:
        kwargs["pitch"] = config.VOICE_PITCH
    communicate = edge_tts.Communicate(text, config.VOICE_NAME, **kwargs)
    buffer = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.extend(chunk["data"])
    if not buffer:
        raise VoiceError("edge-tts no devolvió audio")
    return bytes(buffer)


def _fish_bytes(text: str) -> bytes:
    if not config.FISH_API_KEY:
        raise VoiceError("Falta FISH_API_KEY para usar la voz del JARVIS original")
    resp = httpx.post(
        "https://api.fish.audio/v1/tts",
        headers={"Authorization": f"Bearer {config.FISH_API_KEY}"},
        json={
            "text": text,
            "reference_id": config.FISH_VOICE_ID,
            "format": "mp3",
        },
        timeout=60.0,
    )
    if resp.status_code != 200:
        raise VoiceError(f"Fish Audio devolvió HTTP {resp.status_code}")
    return resp.content


def _say_bytes(text: str) -> bytes:
    if not shutil.which("say"):
        raise VoiceError("`say` no está disponible (solo existe en macOS)")
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        out = Path(tmp.name)
    subprocess.run(["say", "-v", "Daniel", "-o", str(out), text], check=True)
    data = out.read_bytes()
    out.unlink(missing_ok=True)
    return data


def speak(text: str) -> tuple[bytes, str]:
    """Sintetiza `text`. Devuelve (audio, mime). Prueba el proveedor elegido y
    cae al siguiente si falla, para que JARVIS nunca se quede mudo del todo."""
    text = text.strip()
    if not text:
        raise VoiceError("texto vacío")

    order = {
        "edge": ["edge", "say"],
        "fish": ["fish", "edge", "say"],
        "say": ["say", "edge"],
    }.get(config.VOICE_PROVIDER, ["edge", "say"])

    last_error: Exception | None = None
    for provider in order:
        try:
            if provider == "edge":
                return asyncio.run(_edge_bytes(text)), "audio/mpeg"
            if provider == "fish":
                return _fish_bytes(text), "audio/mpeg"
            if provider == "say":
                return _say_bytes(text), "audio/aiff"
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise VoiceError(f"ninguna voz disponible: {last_error}")
