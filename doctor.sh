#!/usr/bin/env bash
# Comprueba si JARVIS puede pensar y hablar, y explica cómo arreglarlo.
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate
exec python -m jarvis.doctor
