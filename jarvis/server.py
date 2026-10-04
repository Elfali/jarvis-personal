"""Servidor de JARVIS: FastAPI + WebSocket + interfaz web.

Endpoints:
  GET  /                 -> interfaz visual (orbe + micrófono)
  GET  /api/health       -> estado del cerebro y la voz
  POST /api/chat         -> {message} -> {reply, audio(base64)}
  POST /api/improve      -> {request} -> aplica auto-mejora
  WS   /ws               -> conversación en streaming simple
"""

from __future__ import annotations

import asyncio
import base64
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, self_improve
from .agent import Agent

app = FastAPI(title="JARVIS Personal")
agent = Agent()
FRONTEND = config.ROOT / "frontend"


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []


class ImproveIn(BaseModel):
    request: str


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/health")
def health() -> dict:
    ok, msg = agent.brain.health()
    return {
        "brain_ok": ok,
        "brain": msg,
        "voice_provider": config.VOICE_PROVIDER,
        "assistant": config.ASSISTANT_NAME,
    }


def _encode(text: str, mime: str | None, audio: bytes | None) -> dict:
    return {
        "reply": text,
        "audio": base64.b64encode(audio).decode() if audio else None,
        "mime": mime,
    }


@app.post("/api/chat")
def chat(payload: ChatIn) -> dict:
    history = [*payload.history, {"role": "user", "content": payload.message}]
    text, mime, audio = agent.respond(history)
    return _encode(text, mime, audio)


@app.post("/api/improve")
def improve(payload: ImproveIn) -> dict:
    summary = self_improve.improve(payload.request, agent.brain)
    text, mime, audio = agent._with_voice(summary)
    return _encode(text, mime, audio)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    history: list[dict] = []
    loop = asyncio.get_running_loop()

    async def ask(tool_name: str, args: dict) -> bool:
        """Pregunta al usuario si autoriza una acción y espera SU respuesta.

        Se lee aquí mismo la respuesta para no bloquear el bucle principal
        (que está ocupado ejecutando el agente). Se pregunta de una en una.
        """
        await ws.send_text(json.dumps({
            "type": "confirm",
            "tool": tool_name,
            "args": args,
            "question": f"¿Autorizas ejecutar «{tool_name}»?",
        }))
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            if "confirm" in data:
                return bool(data["confirm"])

    def confirm(tool_name: str, args: dict) -> bool:
        # Se llama desde el hilo del agente; hay que volver al bucle async.
        fut = asyncio.run_coroutine_threadsafe(ask(tool_name, args), loop)
        return bool(fut.result(timeout=180))

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            message = data.get("message", "")
            if not message:
                continue
            history.append({"role": "user", "content": message})
            await ws.send_text(json.dumps({"type": "thinking"}))
            text, mime, audio = await asyncio.to_thread(agent.respond, history, confirm)
            history.append({"role": "assistant", "content": text})
            await ws.send_text(json.dumps(_encode(text, mime, audio)))
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        await ws.send_text(json.dumps({"reply": f"Error: {exc}", "audio": None}))


# Sirve orb.js y cualquier estático del frontend bajo /static.
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=config.PORT)


if __name__ == "__main__":
    main()
