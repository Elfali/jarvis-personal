# JARVIS personal

Tu propio JARVIS para macOS: visual, con voz, instalable y capaz de mejorarse a
sí mismo cuando se lo ordenas. Inspirado en el JARVIS original, pero construido
para funcionar **gratis** y ser **tuyo**.

```
        hablas  →  cerebro (LLM)  →  herramientas  →  responde con voz
          ↑                                                   │
          └──────────────── orbe visual reactivo ─────────────┘
```

## Qué es gratis y qué no

| Pieza | Por defecto (gratis) | La del JARVIS original (de pago) |
|---|---|---|
| Cerebro | **Ollama** local, privado | Claude Code (suscripción Claude) |
| Voz | **edge-tts** (voz británica `es-ES-AlvaroNeural`, España) | **Fish Audio** (voz idéntica al original) |
| Oído | Web Speech API de Chrome | — |
| Interfaz | Orbe de partículas propio | — |

Cambiar entre gratis y original es **una línea** en `.env`. Nada de lo gratuito
requiere tarjeta.

## Instalación (en tu Mac)

```bash
cd jarvis-personal
./install.sh          # crea el entorno e instala dependencias
```

Instala además, si no los tienes:

```bash
brew install python              # Python 3.10+
brew install --cask ollama       # cerebro local (o usa una API, ver abajo)
```

Descarga un modelo y arranca Ollama:

```bash
ollama pull llama3.1
```

## Arrancar

```bash
./start.sh            # arranca JARVIS y abre Chrome
```

Luego, en Chrome, haz clic en el botón del micrófono y habla.

> El micrófono **solo funciona en Google Chrome** (Web Speech API). Y el permiso
> está ligado al puerto: si cambias `JARVIS_PORT`, Chrome no vuelve a pedirlo.
> Si el micro deja de funcionar, revisa `chrome://settings/content/microphone`.

## Que arranque solo al iniciar sesión

```bash
./install-service.sh  # lo registra como servicio de macOS (launchd)
```

Desactivarlo:

```bash
launchctl unload ~/Library/LaunchAgents/com.jarvis.personal.plist
```

## Que se mejore a sí mismo

Dile, por ejemplo:

- *"JARVIS, añádete una herramienta para consultar el tiempo."*
- *"JARVIS, mejórate: quiero que recuerdes mis proyectos."*

Flujo seguro, sin sorpresas:

1. El cerebro propone los archivos nuevos.
2. Se hace **copia de seguridad** de los originales en `data/backups/`.
3. Se aplica el cambio y se comprueba que todo sigue importando.
4. Si algo se rompe, **se revierte automáticamente**.

Solo funciona bien con un cerebro capaz de programar: un modelo de código en
Ollama (`qwen2.5-coder`, `deepseek-coder`), o una API de las de abajo.

## Elegir el cerebro

Edita `.env`:

**Ollama local (gratis, privado)** — por defecto:

```env
JARVIS_BRAIN_PROVIDER=ollama
JARVIS_BRAIN_MODEL=llama3.1
```

**Una API con capa gratuita** (Groq, Gemini, OpenRouter…):

```env
JARVIS_BRAIN_PROVIDER=openai
JARVIS_BRAIN_BASE_URL=https://api.groq.com/openai/v1
JARVIS_BRAIN_MODEL=llama-3.3-70b-versatile
JARVIS_BRAIN_API_KEY=tu_clave
```

**La del original** (suscripción Claude, requiere `npm i -g @anthropic-ai/claude-code`):

```env
JARVIS_BRAIN_PROVIDER=claude_code
```

## Hacerlo más rápido

Si JARVIS tarda en pensar o hablar, estos ajustes en `.env` ayudan mucho:

| Ajuste | Valor | Efecto |
|---|---|---|
| `JARVIS_BRAIN_MODEL` | `llama3.2` | Modelo ligero: piensa en segundos |
| `JARVIS_BRAIN_MAX_TOKENS` | `160` | Respuestas cortas = habla menos |
| `JARVIS_OLLAMA_KEEP_ALIVE` | `30m` | Mantiene el modelo cargado (sin retraso inicial) |
| `JARVIS_VOICE_RATE` | `-4%` | Voz un poco más ágil |

Con Ollama, descarga el modelo ligero una vez:

```bash
ollama pull llama3.2
```

La mayor mejora viene de **respuestas cortas** (ya activadas): JARVIS responde
en 1 o 2 frases, así piensa y habla mucho menos tiempo. La opción más rápida de
todas es usar una **API en la nube** (Groq responde en menos de un segundo; ver
"Elegir el cerebro").

## Darle acceso a comandos (niveles de permiso)

Por defecto JARVIS solo ejecuta una **lista blanca** de comandos seguros. Puedes
ampliar su acceso con `JARVIS_SHELL_MODE` en `.env`, de menos a más potente:

| Modo | Qué permite | Seguridad |
|---|---|---|
| `allowlist` (por defecto) | Solo la lista de comandos seguros + los que añadas | Máxima |
| `confirm` | **Cualquier** comando, pero pide permiso antes de cada uno | Alta |
| `all` | Cualquier comando sin preguntar | Baja (¡cuidado!) |

Además, en cualquier modo los comandos **destructivos** (`rm`, `sudo`, `dd`,
`shutdown`…) siempre piden confirmación.

### Ejemplos

Permitir comandos concretos sin preguntar:
```env
JARVIS_SHELL_EXTRA_ALLOWED=uptime,df,du,top
```

Permitir cualquiera, con confirmación por cada uno (recomendado si quieres libertad):
```env
JARVIS_SHELL_MODE=confirm
```

Permitir todo sin preguntar (solo si confías plenamente):
```env
JARVIS_SHELL_MODE=all
```

Cuando JARVIS pida permiso, verás un diálogo en la interfaz con el comando exacto
y podrás aceptar o rechazar.

## Si algo no funciona

Ejecuta el diagnóstico, que te dice qué falta y cómo arreglarlo:

```bash
./doctor.sh
```

### "Mi cerebro no responde"

La causa más común es que **Ollama no está instalado o no tiene el modelo**.
Arréglalo todo de una vez con:

```bash
./setup-brain.sh
```

Ese script instala Ollama, lo arranca y descarga el modelo automáticamente.
Después comprueba con `./doctor.sh`.

Si prefieres hacerlo a mano:

```bash
brew install --cask ollama      # si no lo tienes
open -a Ollama                  # arráncalo (o: ollama serve)
ollama pull llama3.1            # descarga el modelo
```

Si no quieres Ollama, usa una API gratuita (sección "Elegir el cerebro").

### "La voz no se entiende"

Estás usando una voz inglesa para texto en español. En `.env` pon una voz
española y reinicia:

```env
JARVIS_VOICE_NAME=es-ES-AlvaroNeural
```

Otras voces: `es-MX-JorgeNeural`, `es-AR-TomasNeural`, `es-ES-ElviraNeural`.
Para oírla antes de arrancar: `./say-test.sh`.

### La voz del JARVIS original (avanzado)

La voz británica idéntica al original es un modelo de **Fish Audio** (de pago).
Pon una voz británica gratis suena a inglés leyendo español, así que para español
usa las voces de arriba. Para la voz exacta, activa Fish (sección siguiente).

## La voz exacta del JARVIS original

La voz del original es un modelo de **Fish Audio** (de pago). Para activarla:

```env
JARVIS_VOICE_PROVIDER=fish
FISH_API_KEY=tu_clave_de_fish_audio
FISH_VOICE_ID=612b878b113047d9a770c069c8b4fdfe
```

Sin clave, JARVIS cae automáticamente a la voz gratuita (nunca se queda mudo).

## Herramientas que ya tiene

| Herramienta | Qué hace |
|---|---|
| `run_shell` | Ejecuta comandos de una lista blanca |
| `read_file` / `write_file` | Lee y escribe archivos |
| `list_dir` | Lista carpetas |
| `open_app` | Abre apps de macOS |
| `system_info` | Información del sistema |
| `remember` / `recall` | Memoria permanente en `data/memory.jsonl` |

`write_file` está marcada como peligrosa: el servidor pide confirmación antes de
sobrescribir. Amplía la lista blanca de comandos en `jarvis/config.py` con
cuidado.

## Estructura

```
jarvis-personal/
├── jarvis/
│   ├── config.py        # ajustes y prompt de personalidad
│   ├── brain.py         # cerebro intercambiable
│   ├── voice.py         # voz intercambiable
│   ├── tools.py         # herramientas
│   ├── self_improve.py  # auto-mejora con copia de seguridad
│   ├── agent.py         # bucle conversación + herramientas
│   └── server.py        # FastAPI + WebSocket
├── frontend/
│   ├── index.html       # interfaz con micrófono
│   └── orb.js           # orbe de partículas
├── tests/test_core.py   # pruebas del núcleo
├── install.sh / start.sh / install-service.sh
└── launchd/             # plantilla de autoarranque
```

## Personalizarlo

- **Personalidad y nombre**: `SYSTEM_PROMPT` en `jarvis/config.py`.
- **Voz**: `JARVIS_VOICE_NAME` (lista con `edge-tts --list-voices`).
- **Nuevas herramientas**: añade una función y un `Tool(...)` en `jarvis/tools.py`.
- **Cómo te llama**: `USER_NAME` en `.env`.

## Pruebas

```bash
source .venv/bin/activate
python tests/test_core.py
```

Cubren herramientas, lista blanca, bucle del agente, confirmación de acciones
peligrosas y la reversión de la auto-mejora.
