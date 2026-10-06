"""Contraseña de acceso a JARVIS.

Si `JARVIS_PASSWORD` está definida, el servidor exige esa contraseña antes de
dejar usar la interfaz o el WebSocket. Es imprescindible si JARVIS está en un
servidor con IP pública: sin ella, cualquiera que dé con la URL podría usar tu
asistente y leer tu memoria.

Al acertar la contraseña se deja una cookie firmada (HMAC). La cookie se envía
sola en el WebSocket porque es del mismo origen.
"""

from __future__ import annotations

import hashlib
import hmac

from . import config

COOKIE = "jarvis_auth"


def activo() -> bool:
    return bool(config.PASSWORD)


def _token() -> str:
    return hmac.new(
        config.PASSWORD.encode("utf-8"), b"jarvis-auth", hashlib.sha256
    ).hexdigest()


def cookie_valida(valor: str | None) -> bool:
    if not activo():
        return True
    if not valor:
        return False
    return hmac.compare_digest(valor, _token())


def comprobar_password(candidata: str | None) -> bool:
    if not activo():
        return True
    if not candidata:
        return False
    return hmac.compare_digest(candidata, config.PASSWORD)


def token_cookie() -> str:
    return _token()


LOGIN_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>JARVIS · Acceso</title>
<style>
  html,body{margin:0;height:100%;background:#05030a;color:#ffd9b0;
    font-family:"SF Mono",Menlo,Consolas,monospace;display:grid;place-items:center}
  form{display:flex;flex-direction:column;gap:14px;width:280px;text-align:center}
  h1{font-size:15px;letter-spacing:4px;color:#ff9a3c;margin:0 0 8px}
  input{padding:11px 14px;background:rgba(255,140,60,.06);
    border:1px solid rgba(255,154,60,.35);color:#ffd9b0;font-family:inherit;
    font-size:14px;outline:none;text-align:center}
  input:focus{border-color:#ff9a3c;box-shadow:0 0 18px rgba(255,140,60,.3)}
  button{padding:11px;border:1px solid #ff9a3c;background:#ff9a3c;color:#140a02;
    font-family:inherit;font-weight:700;letter-spacing:2px;text-transform:uppercase;
    cursor:pointer}
  .err{color:#ff7a5a;font-size:12px;letter-spacing:1px}
</style></head><body>
<form method="post" action="/login">
  <h1>JARVIS</h1>
  <input type="password" name="password" placeholder="Contraseña" autofocus />
  {error}
  <button type="submit">Entrar</button>
</form></body></html>"""
