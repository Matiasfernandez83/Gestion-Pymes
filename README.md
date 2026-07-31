# Gestión PyMEs — Tablero de control

Tablero de control para pequeñas y medianas empresas: centraliza los indicadores de gestión en una sola vista. Full-stack en Python y empaquetado con Docker para desplegar en cualquier entorno.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Render](https://img.shields.io/badge/Render-46E3B7?style=flat&logo=render&logoColor=black)

## Qué hace

- Centraliza los **indicadores de gestión** de una PyME en un solo tablero.
- Carga de datos vía planillas (soporte de archivos Excel).
- Listo para **producción**: incluye configuración de Docker y de Render.

> Videos demo incluidos en el repo: `Demo_Sistema_Pyme.webm` y `Demo_Comercial_4K.webm`.

## Stack

- **Backend:** Python + Flask (servido con `wsgi.py`)
- **Frontend:** HTML / CSS / JavaScript (templates)
- **Contenedor:** Docker
- **Deploy:** Render (`render.yaml`)

## Estructura

```
templates/          Vistas de la app
static/             Assets (CSS, JS, imágenes)
app.py              Aplicación Flask
wsgi.py             Entry point para el servidor de producción
Dockerfile          Imagen del contenedor
render.yaml         Configuración de deploy en Render
requirements.txt
```

## Cómo correrlo

### Opción A — Local con Python

```bash
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # completá los valores
python app.py
```

### Opción B — Con Docker

```bash
docker build -t gestion-pymes .
docker run -p 8000:8000 gestion-pymes
```

La app queda disponible en `http://localhost:8000`.
