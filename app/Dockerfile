FROM python:3.10-slim

WORKDIR /app

# Instalar git y otras dependencias del sistema
RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorios necesarios y enlace simbólico entre /srv/users y /srv/cloudfaster/users
RUN mkdir -p /srv/cloudfaster/users && \
    ln -sf /srv/cloudfaster/users /srv/users

# Copiar el resto del código
COPY . .

# Script de inicialización que ejecuta setup y luego inicia la aplicación
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Puerto en el que se ejecuta la aplicación
EXPOSE 8000

# Comando para ejecutar el script de entrada
ENTRYPOINT ["/entrypoint.sh"] 