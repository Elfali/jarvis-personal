# Imagen de JARVIS. Sirve la interfaz y el servidor; el cerebro puede ser
# local (Ollama en el host) o remoto (Groq/OpenRouter...) vía .env.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY jarvis ./jarvis
COPY frontend ./frontend
COPY .jarvis-root .

# Carpeta de memoria (hechos + conversación). En Docker conviene montarla como
# volumen para que la memoria sobreviva a reinicios y actualizaciones.
RUN mkdir -p /app/data
VOLUME ["/app/data"]

ENV JARVIS_PORT=8765
EXPOSE 8765

# Escucha en todas las interfaces para poder acceder desde fuera del contenedor.
CMD ["python", "-m", "jarvis.server"]
