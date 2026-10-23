FROM python:3.10-slim

# Instalar Chromium y librerías necesarias del sistema
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Iniciar servidor Uvicorn en el puerto que le asigne Render
CMD uvicorn main:app --host 0.0.0.0 --port $PORT