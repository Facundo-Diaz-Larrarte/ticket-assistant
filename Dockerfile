FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema y herramientas necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos e instalar paquetes Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores Playwright y sus dependencias de Linux para modo headless
RUN playwright install chromium --with-deps

# Copiar el código de la aplicación
COPY . .

# Comando de ejecución del monitor 24/7 en segundo plano
CMD ["python", "-m", "app.main", "monitor"]
