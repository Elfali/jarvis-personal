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

from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, config, self_improve
from . import memory as memoria
from .agent import Agent

app = FastAPI(title="JARVIS Personal")
agent = Agent()
FRONTEND = config.ROOT / "frontend"


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []


class ImproveIn(BaseModel):
    request: str


class RememberIn(BaseModel):
    note: str


@app.get("/api/memory")
def get_memory(request: Request, q: str = "", limit: int = 50) -> dict:
    """Devuelve la memoria (hechos y registro) y sus estadísticas."""
    _exigir_auth(request)
    return {
        "notas": memoria.recall(q, limit=limit),
        "historial": memoria.history(limit=limit),
        "stats": memoria.stats(),
    }


@app.post("/api/memory")
def post_memory(payload: RememberIn, request: Request) -> dict:
    """Guarda un hecho duradero en la memoria del servidor."""
    _exigir_auth(request)
    return {"reply": memoria.remember(payload.note), "stats": memoria.stats()}


@app.get("/login")
def login_form() -> HTMLResponse:
    return HTMLResponse(auth.LOGIN_HTML.replace("{error}", ""))


@app.post("/login")
def login(password: str = Form("")) -> Response:
    if auth.comprobar_password(password):
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(
            auth.COOKIE, auth.token_cookie(), httponly=True, samesite="lax"
        )
        return resp
    return HTMLResponse(
        auth.LOGIN_HTML.replace(
            "{error}", '<div class="err">Contraseña incorrecta</div>'
        ),
        status_code=401,
    )


@app.get("/")
def index(request: Request) -> Response:
    if not auth.cookie_valida(request.cookies.get(auth.COOKIE)):
        return RedirectResponse("/login", status_code=303)
    return FileResponse(FRONTEND / "index.html")


def _exigir_auth(request: Request) -> None:
    if not auth.cookie_valida(request.cookies.get(auth.COOKIE)):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="No autorizado")


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
def chat(payload: ChatIn, request: Request) -> dict:
    _exigir_auth(request)
    history = [*payload.history, {"role": "user", "content": payload.message}]
    text, mime, audio = agent.respond(history)
    return _encode(text, mime, audio)


@app.post("/api/improve")
def improve(payload: ImproveIn, request: Request) -> dict:
    _exigir_auth(request)
    summary = self_improve.improve(payload.request, agent.brain)
    text, mime, audio = agent._with_voice(summary)
    return _encode(text, mime, audio)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    # Sin contraseña válida no se acepta la conexión (el WebSocket lleva la
    # cookie del mismo origen, así que el login del navegador la cubre).
    if not auth.cookie_valida(ws.cookies.get(auth.COOKIE)):
        await ws.close(code=4401)
        return
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

    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
