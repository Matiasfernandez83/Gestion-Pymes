"""
Punto de Entrada WSGI (Web Server Gateway Interface)
Obligatorio para que servidores en la nube como Gunicorn
sepan cómo inicializar y ejecutar la aplicación Flask.
"""

from app import app, init_db
import os

# Inicializar DB en caso de estar de despliegue inicial
# Idealmente, en prod esto se corre via comandos, pero aquí asegura 
# el flujo simple sin caídas.
if not os.path.exists("database.db"):
    init_db()

if __name__ == "__main__":
    app.run()
