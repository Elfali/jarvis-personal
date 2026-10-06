"""Pruebas del núcleo de JARVIS con un cerebro simulado (sin red, sin Ollama)."""

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis import self_improve  # noqa: E402
from jarvis.agent import Agent  # noqa: E402
from jarvis.tools import build_tools  # noqa: E402


class FakeBrain:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages, tools=None):
        self.calls.append(messages)
        return self.replies.pop(0)

    def health(self):
        return True, "fake"


def _agent(replies):
    agent = Agent.__new__(Agent)
    agent.brain = FakeBrain(replies)
    agent.tools = {t.name: t for t in build_tools()}
    agent.schemas = [t.schema() for t in agent.tools.values()]
    return agent


def test_tools_registered():
    tools = {t.name: t for t in build_tools()}
    assert "run_shell" in tools and "remember" in tools
    assert tools["write_file"].dangerous is True
    assert tools["read_file"].dangerous is False
    print("OK tools_registered")


def test_shell_allowlist_blocks():
    tools = {t.name: t for t in build_tools()}
    assert "allowlist" in tools["run_shell"].func("rm -rf /")
    assert tools["run_shell"].func("echo hola") == "hola"
    print("OK shell_allowlist_blocks")


def test_agent_plain_reply():
    agent = _agent([{"role": "assistant", "content": "Hola, señor."}])
    text, _, _ = agent.respond([{"role": "user", "content": "hola"}])
    assert text == "Hola, señor.", text
    print("OK agent_plain_reply")


def test_agent_tool_call_roundtrip():
    tool_call = {"id": "1", "function": {"name": "system_info", "arguments": "{}"}}
    agent = _agent([
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        {"role": "assistant", "content": "Estás en un Mac."},
    ])
    text, _, _ = agent.respond([{"role": "user", "content": "¿qué sistema es?"}])
    assert text == "Estás en un Mac.", text
    assert any(m.get("role") == "tool" for m in agent.brain.calls[1])
    print("OK agent_tool_call_roundtrip")


def test_dangerous_tool_needs_confirmation():
    tool_call = {
        "id": "1",
        "function": {"name": "write_file", "arguments": '{"path":"/tmp/x","content":"y"}'},
    }
    agent = _agent([
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        {"role": "assistant", "content": "No lo hice."},
    ])
    agent.respond([{"role": "user", "content": "escribe"}])
    tool_msgs = [m for m in agent.brain.calls[1] if m.get("role") == "tool"]
    assert tool_msgs and "no autorizó" in tool_msgs[0]["content"]
    assert not Path("/tmp/x").exists()
    print("OK dangerous_tool_needs_confirmation")


def test_self_improve_reverts_on_broken_code():
    brain = FakeBrain([{
        "role": "assistant",
        "content": json.dumps({
            "summary": "rompo todo",
            "files": {"jarvis/brain.py": "esto no es python"},
        }),
    }])
    result = self_improve.improve("rompe el cerebro", brain)
    assert "revertí" in result, result
    import jarvis.brain

    importlib.reload(jarvis.brain)
    print("OK self_improve_reverts_on_broken_code")


def test_self_improve_applies_valid_change():
    path = self_improve.SELF_DIR / "config.py"
    original = path.read_text()
    new_content = original.replace(
        'ASSISTANT_NAME = get("JARVIS_NAME", "JARVIS")',
        'ASSISTANT_NAME = get("JARVIS_NAME", "JARVIS-2")',
    )
    brain = FakeBrain([{
        "role": "assistant",
        "content": json.dumps({"summary": "renombrado",
                               "files": {"jarvis/config.py": new_content}}),
    }])
    result = self_improve.improve("cámbiate el nombre", brain)
    assert "renombrado" in result, result
    assert "JARVIS-2" in path.read_text()
    path.write_text(original)
    print("OK self_improve_applies_valid_change")


def test_shell_modes():
    from jarvis import config
    from jarvis.tools import _shell_needs_confirmation
    original = config.SHELL_MODE
    try:
        config.SHELL_MODE = "confirm"
        assert _shell_needs_confirmation({"command": "echo hola"}) is True
        config.SHELL_MODE = "all"
        assert _shell_needs_confirmation({"command": "echo hola"}) is False
        config.SHELL_MODE = "allowlist"
        assert _shell_needs_confirmation({"command": "echo hola"}) is False
        assert _shell_needs_confirmation({"command": "rm -rf /"}) is True
    finally:
        config.SHELL_MODE = original
    print("OK shell_modes")


def test_ws_confirmation_does_not_deadlock():
    """El servidor debe pedir permiso y seguir tras la respuesta del usuario."""
    import asyncio
    import threading
    import time

    import uvicorn

    from jarvis import server

    class Brain:
        def __init__(self):
            self.n = 0

        def chat(self, messages, tools=None):
            self.n += 1
            if self.n == 1:
                return {"role": "assistant", "content": None, "tool_calls": [{
                    "id": "1",
                    "function": {"name": "write_file",
                                 "arguments": json.dumps({"path": "/tmp/jarvis_ws_test.txt",
                                                          "content": "ok"})},
                }]}
            return {"role": "assistant", "content": "Hecho."}

        def health(self):
            return True, "fake"

    server.agent.brain = Brain()
    server.agent._with_voice = lambda text: (text, None, None)

    cfg = uvicorn.Config(server.app, host="127.0.0.1", port=8802, log_level="warning")
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, daemon=True).start()
    time.sleep(1.5)

    import websockets

    async def flow():
        async with websockets.connect("ws://127.0.0.1:8802/ws") as ws:
            await ws.send(json.dumps({"message": "escribe un archivo"}))
            first = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            assert first.get("type") == "thinking", first
            second = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            assert second.get("type") == "confirm", second
            await ws.send(json.dumps({"confirm": True}))
            final = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            assert final.get("reply") == "Hecho.", final

    asyncio.run(flow())
    print("OK ws_confirmation_does_not_deadlock")


def test_history_trimming():
    from jarvis import config
    from jarvis.agent import Agent

    original = config.HISTORY_MAX_TURNS
    try:
        config.HISTORY_MAX_TURNS = 4
        history = [{"role": "user", "content": f"m{i}"} for i in range(10)]
        trimmed = Agent._trim(history)
        assert len(trimmed) == 4, trimmed
        assert trimmed[-1]["content"] == "m9"
        # Con el límite desactivado no se recorta nada.
        config.HISTORY_MAX_TURNS = 0
        assert len(Agent._trim(history)) == 10
    finally:
        config.HISTORY_MAX_TURNS = original
    print("OK history_trimming")


def test_tool_rounds_is_bounded():
    from jarvis import config
    assert 1 <= config.TOOL_ROUNDS <= 6, config.TOOL_ROUNDS
    assert config.BRAIN_NUM_CTX >= 0
    print("OK tool_rounds_bounded")


def test_protocolo_caida_seguridad():
    """El autodestructivo no debe dispararse sin la frase exacta ni sin marcador."""
    from jarvis import config, protocolo_caida

    # Frase incorrecta: no borra nada.
    r = protocolo_caida.ejecutar("haz el protocolo caida")
    assert "NO ejecutado" in r, r
    # Frase correcta pero en modo ensayo: solo lista, no borra.
    r = protocolo_caida.ejecutar(protocolo_caida.FRASE, ensayo=True)
    assert "Ensayo" in r, r
    # La raíz debe tener el marcador de seguridad.
    assert (Path(config.ROOT) / protocolo_caida.MARCADOR).is_file()
    assert protocolo_caida._raiz_segura() is not None
    print("OK protocolo_caida_seguridad")


def test_protocolo_caida_no_borra_fuera_de_raiz():
    """Todas las rutas del proyecto a borrar deben estar dentro de la raíz."""
    from jarvis import config, protocolo_caida

    raiz = Path(config.ROOT).resolve()
    for ruta in protocolo_caida._rutas_a_borrar():
        rp = ruta.resolve()
        dentro_proyecto = raiz in rp.parents or rp == raiz
        dentro_home = Path.home() in rp.parents
        assert dentro_proyecto or dentro_home, rp
        # Nunca el home entero.
        assert rp != Path.home()
    print("OK protocolo_caida_no_borra_fuera_de_raiz")


def test_protocolo_caida_integracion_agent():
    """Dentro del agente, solo dispara si está activo y la frase es exacta."""
    from jarvis import config

    original = config.PROTOCOLO_CAIDA_ACTIVO
    try:
        config.PROTOCOLO_CAIDA_ACTIVO = False
        agent = _agent([{"role": "assistant", "content": "Hola."}])
        text, _, _ = agent.respond([{"role": "user", "content": "PROTOCOLO CAIDA"}])
        assert text == "Hola.", text  # desactivado: no dispara
    finally:
        config.PROTOCOLO_CAIDA_ACTIVO = original
    print("OK protocolo_caida_integracion_agent")


def test_memory_persistente():
    """La memoria se guarda en disco y sobrevive (servidor)."""
    import tempfile
    from pathlib import Path as P

    from jarvis import config, memory

    original = config.DATA_DIR
    tmp = P(tempfile.mkdtemp())
    try:
        config.DATA_DIR = tmp
        memory.remember("Marco usa MacBook Air")
        memory.remember("A Marco le gusta el cafe")
        memory.save_turn("hola", "hola, senor")
        # Releer desde disco, como tras un reinicio del servidor.
        assert "MacBook Air" in memory.recall()
        assert "cafe" in memory.recall("cafe")
        assert "MacBook" not in memory.recall("cafe")
        h = memory.history()
        assert h and h[-1]["user"] == "hola"
        s = memory.stats()
        assert s["notas"] == 2 and s["turnos"] == 1, s
        assert (tmp / "memory.jsonl").exists()
        assert (tmp / "history.jsonl").exists()
    finally:
        config.DATA_DIR = original
    print("OK memory_persistente")


def test_memory_se_inyecta_en_el_prompt():
    """Los hechos memorizados deben aparecer en el prompt del sistema."""
    import tempfile
    from pathlib import Path as P

    from jarvis import config, memory

    original_dir = config.DATA_DIR
    tmp = P(tempfile.mkdtemp())
    try:
        config.DATA_DIR = tmp
        memory.remember("El usuario se llama Marco")
        agent = _agent([])
        sistema = agent._system()["content"]
        assert "Marco" in sistema, sistema
    finally:
        config.DATA_DIR = original_dir
    print("OK memory_se_inyecta_en_el_prompt")


def test_memory_autolearn_no_rompe():
    """Si el cerebro devuelve basura, el aprendizaje automático no falla."""
    from jarvis import memory

    class Basura:
        def chat(self, messages, tools=None):
            return {"role": "assistant", "content": "esto no es json"}

    assert memory.extract_facts(Basura(), "hola", "hola") == []
    print("OK memory_autolearn_no_rompe")


def test_auth_password():
    """La contraseña protege el acceso y la cookie firmada es válida."""
    from jarvis import auth, config

    original = config.PASSWORD
    try:
        config.PASSWORD = ""
        assert not auth.activo()
        assert auth.cookie_valida(None)  # sin contraseña, todo permitido

        config.PASSWORD = "secreta123"
        assert auth.activo()
        assert not auth.cookie_valida(None)
        assert not auth.cookie_valida("inventada")
        assert auth.comprobar_password("secreta123")
        assert not auth.comprobar_password("otra")
        assert not auth.comprobar_password(None)
        assert auth.cookie_valida(auth.token_cookie())
    finally:
        config.PASSWORD = original
    print("OK auth_password")


if __name__ == "__main__":
    test_tools_registered()
    test_shell_allowlist_blocks()
    test_shell_modes()
    test_agent_plain_reply()
    test_agent_tool_call_roundtrip()
    test_dangerous_tool_needs_confirmation()
    test_ws_confirmation_does_not_deadlock()
    test_history_trimming()
    test_tool_rounds_is_bounded()
    test_protocolo_caida_seguridad()
    test_protocolo_caida_no_borra_fuera_de_raiz()
    test_protocolo_caida_integracion_agent()
    test_memory_persistente()
    test_memory_se_inyecta_en_el_prompt()
    test_memory_autolearn_no_rompe()
    test_auth_password()
    test_self_improve_reverts_on_broken_code()
    test_self_improve_applies_valid_change()
    print("\nTODAS LAS PRUEBAS PASARON")
