#!/bin/bash
set -e

# Esperar a que MySQL esté listo
echo "Esperando a que MySQL esté listo..."
sleep 5

# Ejecutar el script de inicialización de la base de datos
echo "Inicializando la base de datos..."
python -m core.db_init

# Guardar la clave API en un archivo para referencia
echo "API key creada y almacenada en /app/api_key.txt"
python -c "from core.db import fetch_one; print(fetch_one('SELECT api_key FROM api_keys ORDER BY id LIMIT 1')[0])" > /app/api_key.txt
cat /app/api_key.txt

# Ejecutar la aplicación FastAPI
echo "Iniciando la aplicación FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload 