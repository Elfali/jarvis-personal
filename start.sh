#!/usr/bin/env bash
# Arranca JARVIS y abre la interfaz en Chrome (el micrófono solo va en Chrome).
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

PORT="${JARVIS_PORT:-8765}"
URL="http://localhost:${PORT}"

( sleep 2; open -a "Google Chrome" "$URL" >/dev/null 2>&1 || open "$URL" ) &

exec python -m jarvis
