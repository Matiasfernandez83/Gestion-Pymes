# Imagen oficial y ligera de Python
FROM python:3.11-slim-bullseye

# Prevenir que Python escriba archivos .pyc en disco y enviar logs en vivo a consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV SECRET_KEY="clave_super_secreta_pymes_prod"

# Establecer directorio de trabajo en la nube
WORKDIR /app

# Instalar dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar configuración de requerimientos e instalar (aprovecha cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Crear un usuario no-root por seguridad
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Exponer el puerto al exterior (por defecto 5000 o 10000 según Render)
EXPOSE 5000

# Comando para ejecutar la app en servidor de producción (Gunicorn)
# Configurado para ser ligero: 2 workers, puerto dinámico de Render
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 wsgi:app
