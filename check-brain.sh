#!/usr/bin/env bash
# Comprueba el cerebro usando solo curl (no necesita el entorno Python).
# Uso:  bash check-brain.sh
set -uo pipefail

echo "================================================================"
echo "  Comprobación del cerebro (Ollama)"
echo "================================================================"

# 1. ¿Está el comando ollama?
if command -v ollama >/dev/null; then
  echo "✅ Comando ollama encontrado: $(command -v ollama)"
else
  echo "❌ El comando 'ollama' no está en el PATH."
  echo "   Instala Ollama desde https://ollama.com/download/mac"
  exit 1
fi

# 2. ¿Responde el servidor?
echo
echo "--> Probando el servidor en http://127.0.0.1:11434 ..."
if ! curl -s --max-time 5 http://127.0.0.1:11434/api/tags >/tmp/jarvis_tags.json 2>/dev/null; then
  echo "❌ El servidor de Ollama NO responde."
  echo "   Abre la app Ollama (la llama en la barra de menús) y espera 10 segundos."
  echo "   Si sigue igual, en otra terminal ejecuta:  ollama serve"
  exit 1
fi
echo "✅ El servidor de Ollama responde."

# 3. ¿Hay modelos descargados?
echo
echo "--> Modelos instalados:"
MODELS="$(python3 -c 'import json,sys;print(" ".join(m.get("name","") for m in json.load(open("/tmp/jarvis_tags.json")).get("models",[])))' 2>/dev/null || true)"
if [ -z "$MODELS" ]; then
  echo "❌ No hay NINGÚN modelo descargado."
  echo "   Descarga uno con:  ollama pull llama3.1"
  echo "   (tarda unos minutos, son ~4 GB)"
  exit 1
fi
echo "   $MODELS"

# 4. ¿Está el modelo que usa JARVIS?
MODEL="llama3.1"
if [ -f .env ]; then
  M="$(grep -E '^JARVIS_BRAIN_MODEL=' .env | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
  [ -n "$M" ] && MODEL="$M"
fi
echo
echo "--> Modelo configurado en JARVIS: $MODEL"
if echo "$MODELS" | tr ' ' '\n' | grep -qx "$MODEL" || echo "$MODELS" | tr ' ' '\n' | grep -qx "${MODEL}:latest"; then
  echo "✅ El modelo está descargado."
else
  echo "❌ El modelo '$MODEL' NO está descargado."
  echo "   Descárgalo con:  ollama pull $MODEL"
  echo "   O cambia JARVIS_BRAIN_MODEL en .env a uno de los que tienes."
  exit 1
fi

# 5. Prueba real de respuesta.
echo
echo "--> Pidiendo una respuesta de prueba al modelo ..."
RESP="$(curl -s --max-time 120 http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Di solo: ok\"}]}")"
if echo "$RESP" | grep -q '"content"'; then
  echo "✅ El cerebro responde correctamente."
  echo
  echo "==> Todo bien. REINICIA JARVIS:  bash start.sh"
else
  echo "❌ El modelo no dio respuesta. Respuesta del servidor:"
  echo "$RESP" | head -c 300
  echo
fi
