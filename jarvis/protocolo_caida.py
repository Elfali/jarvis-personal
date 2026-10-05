"""Protocolo Caída: elimina JARVIS por completo de este ordenador.

Es un autodestructivo: borra la carpeta del proyecto, la configuración del
usuario (~/.jarvis), los modelos descargados de Ollama, el lanzador y las
entradas de arranque automático. Está pensado para "no dejar rastro".

Seguridad (importante):
  - NO se dispara por accidente ni por una frase dicha al aire.
  - Exige una frase de activación EXACTA y ARMADO EXPLÍCITO por dos vías.
  - Solo borra dentro de la carpeta que contiene el marcador `.jarvis-root`.
    Si el marcador no existe, se niega a borrar nada.
  - Nunca toca $HOME entero ni rutas de sistema.
  - Deja un registro en ~/.jarvis/protocolo-caida.log antes de desaparecer.

Uso (terminal):
    python -m jarvis.protocolo_caida --confirmar "PROTOCOLO CAIDA"
    python -m jarvis.protocolo_caida --ensayo     # solo muestra qué haría
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import config

# Frase de activación exacta (sin distinguir mayúsculas ni espacios sobrantes).
FRASE = "PROTOCOLO CAIDA"

# Marcador que identifica la raíz del proyecto. Sin él no se borra nada.
MARCADOR = ".jarvis-root"

# Archivos y carpetas del proyecto que se eliminan por completo.
# `.env` y `data/` contienen secretos y datos: deben desaparecer.
RUTAS_PROYECTO = [
    ".venv",
    "data",
    ".env",
    ".env.example",
    "requirements.txt",
    "setup-brain.sh",
    "start.sh",
    "doctor.sh",
    "README.md",
    ".git",
    ".jarvis-root",
    "jarvis",
    "frontend",
    "tests",
    "pyproject.toml",
    ".gitignore",
]

# Rutas fuera del proyecto (configuración del usuario). Nunca $HOME entero.
def _rutas_usuario() -> list[Path]:
    home = Path.home()
    rutas = [home / ".jarvis"]
    # Lanzador de escritorio / arranque automático.
    rutas += [
        home / "Library" / "LaunchAgents" / "com.jarvis.personal.plist",
        home / ".config" / "autostart" / "jarvis.desktop",
        home / ".local" / "bin" / "jarvis",
    ]
    return rutas


def _log(mensaje: str) -> None:
    """Deja constancia en ~/.jarvis antes de borrarlo (o en /tmp si falla)."""
    try:
        carpeta = Path.home() / ".jarvis"
        carpeta.mkdir(parents=True, exist_ok=True)
        with (carpeta / "protocolo-caida.log").open("a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {mensaje}\n")
    except Exception:  # noqa: BLE001
        pass


def _raiz_segura() -> Path | None:
    """Devuelve la raíz del proyecto solo si el marcador de seguridad existe."""
    raiz = Path(config.ROOT).resolve()
    if not (raiz / MARCADOR).is_file():
        return None
    # Nunca aceptamos rutas peligrosamente amplias.
    if raiz == Path.home() or raiz == Path("/") or len(raiz.parts) < 3:
        return None
    return raiz


def _rutas_a_borrar() -> list[Path]:
    raiz = _raiz_segura()
    if raiz is None:
        return []
    rutas = [raiz / r for r in RUTAS_PROYECTO]
    rutas += _rutas_usuario()
    # Solo devolvemos lo que existe y está dentro de un sitio permitido.
    return [p for p in rutas if p.exists()]


def _borrar_ollama() -> list[str]:
    """Elimina los modelos de Ollama que pertenecen a JARVIS. Devuelve avisos."""
    avisos: list[str] = []
    if shutil.which("ollama") is None:
        return avisos
    modelo = config.BRAIN_MODEL
    try:
        proc = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=30
        )
        presentes = proc.stdout or ""
        if modelo.split(":")[0] in presentes:
            subprocess.run(["ollama", "rm", modelo], capture_output=True, timeout=60)
            avisos.append(f"modelo de Ollama '{modelo}' eliminado")
        else:
            avisos.append(f"el modelo '{modelo}' no estaba descargado")
    except Exception as exc:  # noqa: BLE001
        avisos.append(f"no pude consultar Ollama: {exc}")
    return avisos


def _matar_procesos() -> None:
    """Detiene el servidor de JARVIS si está corriendo."""
    for patron in ("jarvis.server", "jarvis/__main__"):
        try:
            subprocess.run(["pkill", "-f", patron], capture_output=True, timeout=10)
        except Exception:  # noqa: BLE001
            pass


def ejecutar(confirmacion: str | None, ensayo: bool = False) -> str:
    """Ejecuta el Protocolo Caída. Devuelve un resumen de lo ocurrido."""
    raiz = _raiz_segura()
    if raiz is None:
        return (
            "Protocolo Caída abortado por seguridad: no encuentro el marcador "
            f"'{MARCADOR}' en la raíz del proyecto. No he borrado nada."
        )

    rutas = _rutas_a_borrar()

    # El ensayo es inofensivo: solo lista lo que se borraría, sin exigir frase.
    if ensayo:
        return "Ensayo del Protocolo Caída. Borraría:\n  - " + "\n  - ".join(
            str(p) for p in rutas
        ) + "\n(y los modelos de Ollama de JARVIS)"

    if (confirmacion or "").strip().upper() != FRASE:
        return (
            "Protocolo Caída NO ejecutado: la frase de confirmación no coincide. "
            f"Escribe exactamente: {FRASE}"
        )

    borrados: list[str] = []
    fallos: list[str] = []

    _log(f"Protocolo Caída iniciado. Raíz: {raiz}. Rutas: {len(rutas)}")
    _matar_procesos()

    for ruta in rutas:
        try:
            if ruta.is_dir() and not ruta.is_symlink():
                shutil.rmtree(ruta, ignore_errors=False)
            else:
                ruta.unlink(missing_ok=True)
            borrados.append(str(ruta))
        except Exception as exc:  # noqa: BLE001
            fallos.append(f"{ruta}: {exc}")

    avisos = _borrar_ollama()
    _log(f"Protocolo Caída terminado. Borrados: {len(borrados)}. Fallos: {len(fallos)}")

    resumen = [f"Protocolo Caída ejecutado. Elementos eliminados: {len(borrados)}."]
    if fallos:
        resumen.append("Fallos: " + "; ".join(fallos))
    if avisos:
        resumen.append("Ollama: " + "; ".join(avisos))
    resumen.append("JARVIS ha sido eliminado de este ordenador.")
    return " ".join(resumen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jarvis.protocolo_caida",
        description="Elimina JARVIS por completo (autodestructivo).",
    )
    parser.add_argument(
        "--confirmar",
        metavar="FRASE",
        help=f'Frase de activación exacta: "{FRASE}"',
    )
    parser.add_argument(
        "--ensayo",
        action="store_true",
        help="Solo muestra lo que se borraría, sin tocar nada.",
    )
    args = parser.parse_args(argv)
    print(ejecutar(args.confirmar, ensayo=args.ensayo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
