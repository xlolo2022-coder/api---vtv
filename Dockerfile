FROM ubuntu:22.04

# Evitar que el instalador pida confirmaciones interactivas
ENV DEBIAN_FRONTEND=noninteractive

# Instalar Python, pip, Chromium y dependencias del sistema
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    chromium-browser \
    chromium-chromedriver \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

# Iniciar servidor Uvicorn usando python3
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
