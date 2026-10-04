#!/usr/bin/env bash
# Instala JARVIS como servicio de macOS (arranca solo al iniciar sesión).
set -euo pipefail

cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
PLIST_SRC="launchd/com.jarvis.personal.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.jarvis.personal.plist"

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__PROJECT_DIR__|${PROJECT_DIR}|g" "$PLIST_SRC" > "$PLIST_DST"

launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "==> JARVIS instalado como servicio."
echo "    Arranca solo al iniciar sesión y se reinicia si se cae."
echo "    Desactivar: launchctl unload $PLIST_DST"
