#!/usr/bin/env bash
# Instala y arranca el cerebro de JARVIS (Ollama) y descarga el modelo.
# Uso:  ./setup-brain.sh
set -uo pipefail

cd "$(dirname "$0")"

# Lee el modelo y la URL del .env (o usa valores por defecto).
MODEL="llama3.2"
if [ -f .env ]; then
  # shellcheck disable=SC1091
  MODEL="$(grep -E '^JARVIS_BRAIN_MODEL=' .env | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
  [ -z "$MODEL" ] && MODEL="llama3.2"
fi

echo "==> Cerebro de JARVIS: Ollama + modelo '$MODEL'"

# 1. Homebrew (o instalación manual de Ollama)
if ! command -v brew >/dev/null; then
  if command -v ollama >/dev/null; then
    echo "✅ Ollama ya está instalado (sin Homebrew)"
  else
    echo "❌ No tienes Homebrew, y hace falta para instalar Ollama automáticamente."
    echo
    echo "Tienes dos opciones:"
    echo
    echo "  OPCIÓN A — Instalar Ollama a mano (rápido, recomendado):"
    echo "     1) Abre:  https://ollama.com/download/mac"
    echo "     2) Descarga el .dmg, ábrelo y arrastra Ollama a Aplicaciones."
    echo "     3) Abre la app Ollama."
    echo "     4) Vuelve aquí y ejecuta:  bash setup-brain.sh"
    echo
    echo "  OPCIÓN B — Instalar Homebrew (una sola línea):"
    echo '     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo "     Después:  bash setup-brain.sh"
    echo
    echo "  OPCIÓN C — Sin Ollama ni Homebrew: usa una API gratuita (Groq)."
    echo "     Mira el README, sección 'Elegir el cerebro'. No requiere descargas."
    exit 1
  fi
fi

# 2. Ollama
if ! command -v ollama >/dev/null; then
  echo "==> Instalando Ollama…"
  brew install --cask ollama || {
    echo "❌ Falló la instalación de Ollama. Prueba a mano: https://ollama.com/download"
    exit 1
  }
else
  echo "✅ Ollama ya está instalado"
fi

# 3. Arrancar el servidor de Ollama si no está escuchando.
if ! curl -s --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "==> Arrancando Ollama…"
  open -a Ollama 2>/dev/null || (nohup ollama serve >/tmp/ollama.log 2>&1 &)
  for _ in $(seq 1 20); do
    curl -s --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep 1
  done
fi

if ! curl -s --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "❌ Ollama no responde en http://127.0.0.1:11434"
  echo "   Abre la app Ollama y vuelve a ejecutar este script."
  exit 1
fi
echo "✅ Ollama está corriendo"

# 4. Descargar el modelo si falta.
if ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$MODEL" || \
   ollama list 2>/dev/null | awk '{print $1}' | grep -qx "${MODEL}:latest"; then
  echo "✅ El modelo '$MODEL' ya está descargado"
else
  echo "==> Descargando el modelo '$MODEL' (puede tardar unos minutos)…"
  ollama pull "$MODEL" || {
    echo "❌ No se pudo descargar '$MODEL'."
    echo "   Prueba otro modelo ligero:  ollama pull llama3.2"
    exit 1
  }
fi

# 5. Prueba real.
echo "==> Probando el cerebro…"
if curl -s --max-time 120 http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Di solo: ok\"}]}" \
  | grep -q '"content"'; then
  echo "✅ El cerebro funciona"
else
  echo "⚠️  Ollama corre pero no dio respuesta. Revisa:  ./doctor.sh"
fi

echo
echo "==> Listo. Comprueba todo con:  ./doctor.sh"
echo "    Y arranca con:              ./start.sh"
