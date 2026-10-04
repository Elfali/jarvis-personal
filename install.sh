#!/usr/bin/env bash
# Instalador de JARVIS personal para macOS.
set -euo pipefail

cd "$(dirname "$0")"
echo "==> Instalando JARVIS personal"

# 1. Python
if ! command -v python3 >/dev/null; then
  echo "Necesitas Python 3.10+. Instálalo con: brew install python"
  exit 1
fi

# 2. Entorno virtual
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

# 3. Configuración
if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Creado .env (revísalo: cerebro y voz)"
fi

echo
echo "==> Instalación completa."
echo "    Arranca con:  ./start.sh"
echo "    Luego abre Google Chrome en http://localhost:8765"
