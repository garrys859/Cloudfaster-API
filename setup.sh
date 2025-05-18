#!/bin/bash

# Script de configuración automática para el proyecto Cloudfaster
set -e  # Salir inmediatamente si cualquier comando falla

echo "=== Configurando proyecto Cloudfaster ==="

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "Docker no está instalado. Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker ha sido instalado. Por favor, reinicie su sesión para aplicar los cambios de grupo."
    exit 1
fi

# Verificar si Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose no está instalado. Instalando Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose ha sido instalado."
fi

# Solicitar nombre de dominio
DEFAULT_DOMAIN="lpachristian.com"
read -p "Ingrese el nombre de dominio a utilizar [$DEFAULT_DOMAIN]: " DOMAIN_NAME
DOMAIN_NAME=${DOMAIN_NAME:-$DEFAULT_DOMAIN}
echo "Se utilizará el dominio: $DOMAIN_NAME"

# Solicitar token de API de Cloudflare si no está en el entorno
if [ -z "$CF_API_TOKEN" ]; then
    echo "No se encontró la variable de entorno CF_API_TOKEN."
    read -p "Por favor, ingrese su token de API de Cloudflare (necesario para SSL): " CF_API_TOKEN
    # Agregar el token al archivo .env para uso futuro
    echo "CF_API_TOKEN=$CF_API_TOKEN" > .env
    echo "DOMAIN_NAME=$DOMAIN_NAME" >> .env
    echo "Token y dominio guardados en archivo .env"
else
    echo "DOMAIN_NAME=$DOMAIN_NAME" > .env
    echo "CF_API_TOKEN=$CF_API_TOKEN" >> .env
    echo "Dominio guardado en archivo .env"
fi

# Exportar las variables para que estén disponibles en este script
export CF_API_TOKEN
export DOMAIN_NAME

# Crear la red de Docker si no existe
if ! docker network ls | grep -q caddy_net; then
    echo "Creando red de Docker 'caddy_net'..."
    docker network create caddy_net
fi

# Crear directorios necesarios
echo "Creando directorios necesarios..."
# Directorios para Caddy
mkdir -p caddy_data
mkdir -p caddy_config
mkdir -p conf.d

# Directorios para usuarios y asignar permisos adecuados
sudo mkdir -p /srv/cloudfaster/users
sudo chmod -R 755 /srv/cloudfaster
# Permisos para que Docker pueda escribir en estos directorios
sudo chown -R $USER:$USER /srv/cloudfaster

# Verificar si estamos en el directorio correcto
if [ -d "app" ]; then
    echo "Directorio 'app' encontrado."
else
    echo "No se encontró el directorio 'app'. Por favor, ejecute este script desde el directorio raíz del proyecto."
    exit 1
fi

# Verificar y configurar Caddyfile si no existe
if [ ! -f "Caddyfile" ]; then
    echo "Creando Caddyfile..."
    cat > Caddyfile <<EOL
{
	email your-email@example.com
	acme_dns cloudflare {$CF_API_TOKEN}
}

$DOMAIN_NAME {
	respond "Dominio principal" 200
}

api.$DOMAIN_NAME {
	reverse_proxy cloudfaster-api:8000
}

*.$DOMAIN_NAME {
	respond "Servicio no configurado para este subdominio. ¿Aquí debería de estar tu aplicación? Contacte con nosotros." 404
}
EOL
    echo "Caddyfile creado. Por favor, actualice el correo electrónico en el archivo Caddyfile."
fi

# Verificar y crear Dockerfile para Caddy si no existe
if [ ! -f "Dockerfile" ]; then
    echo "Creando Dockerfile para Caddy..."
    cat > Dockerfile <<EOL
# syntax=docker/dockerfile:1
FROM caddy:2.10.0-builder AS builder

RUN xcaddy build \\
  --with github.com/caddy-dns/cloudflare \\
  --with github.com/lucaslorentz/caddy-docker-proxy/v2

FROM caddy:2.10.0

COPY --from=builder /usr/bin/caddy /usr/bin/caddy

CMD ["caddy", "docker-proxy", "--caddyfile-path", "/etc/caddy/Caddyfile"]
EOL
    echo "Dockerfile para Caddy creado."
fi

# Verificar y crear docker-compose.yml para Caddy si no existe
if [ ! -f "docker-compose.yml" ]; then
    echo "Creando docker-compose.yml para Caddy..."
    cat > docker-compose.yml <<EOL
version: "3.9"

services:
  caddy:
    build: .
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./caddy_data:/data
      - ./caddy_config:/config
      - ./conf.d:/etc/caddy/conf.d
    environment:
      CF_API_TOKEN: "\${CF_API_TOKEN}"
      DOMAIN_NAME: "\${DOMAIN_NAME}"
      CADDY_INGRESS_NETWORKS: caddy_net
      LOG_LEVEL: "info"
    networks:
      - caddy_net

networks:
  caddy_net:
    external: true
EOL
    echo "docker-compose.yml para Caddy creado."
fi

# Actualizar app/services/docker_templates.py para usar el dominio definido
echo "Actualizando plantillas de Docker con el dominio $DOMAIN_NAME..."
if [ -f "app/services/docker_templates.py" ]; then
    sed -i "s/lpachristian.com/$DOMAIN_NAME/g" app/services/docker_templates.py
    echo "Plantillas actualizadas."
else
    echo "No se encontró el archivo de plantillas (app/services/docker_templates.py)."
fi

# Actualizar app/services/docker_service.py para usar el dominio definido
echo "Actualizando servicio de Docker con el dominio $DOMAIN_NAME..."
if [ -f "app/services/docker_service.py" ]; then
    sed -i "s/lpachristian.com/$DOMAIN_NAME/g" app/services/docker_service.py
    echo "Servicio Docker actualizado."
else
    echo "No se encontró el archivo del servicio Docker (app/services/docker_service.py)."
fi

# Modificar el archivo app/core/config.py para incluir la variable de entorno DOMAIN_NAME si existe
if [ -f "app/core/config.py" ]; then
    echo "Actualizando configuración para incluir el dominio..."
    # Verificar si ya existe la configuración de DOMAIN_NAME
    if grep -q "DOMAIN_NAME" "app/core/config.py"; then
        echo "La configuración de dominio ya existe en app/core/config.py."
    else
        # Añadir la configuración al final de la clase Settings
        sed -i '/class Settings/,/^$/s/^}/    DOMAIN_NAME: str = os.getenv("DOMAIN_NAME", "lpachristian.com")\n}/' app/core/config.py
        echo "Configuración de dominio añadida a app/core/config.py."
    fi
fi

# Configurar e iniciar la API
echo "Configurando e iniciando la API..."
cd app

# Verificar si los archivos de Docker están presentes
if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ]; then
    echo "No se encontraron los archivos docker-compose.yml o Dockerfile en el directorio app."
    echo "Asegúrese de que estos archivos están presentes antes de continuar."
    exit 1
fi

# No es necesario modificar el docker-compose.yml ya que ya tiene la variable DOMAIN_NAME
# Solo verificamos que existe para informar al usuario
if grep -q "DOMAIN_NAME" "docker-compose.yml"; then
    echo "La variable DOMAIN_NAME ya está configurada en el docker-compose.yml de la aplicación."
else
    echo "Añadiendo variable DOMAIN_NAME al entorno de los servicios en docker-compose.yml..."
    # Modificamos de manera segura para mantener la estructura YAML
    cp docker-compose.yml docker-compose.yml.bak
    awk '
    /environment:/ {
        print $0
        getline
        if (!index($0, "DOMAIN_NAME")) {
            print "      - DOMAIN_NAME=${DOMAIN_NAME}"
        }
        print $0
        next
    }
    { print }
    ' docker-compose.yml.bak > docker-compose.yml
    echo "Variable DOMAIN_NAME añadida correctamente."
fi

# Construir y levantar los contenedores
echo "Construyendo y levantando los contenedores de la API..."
docker-compose down || true  # Por si ya estaban corriendo
docker-compose build
docker-compose up -d
cd ..

# Iniciar Caddy
echo "Configurando e iniciando Caddy..."
docker-compose down || true  # Por si ya estaba corriendo
docker-compose build
docker-compose up -d

# Esperar a que la API esté lista
echo "Esperando a que la API esté lista..."
sleep 15

# Obtener la clave API
API_KEY=$(docker logs cloudfaster-api 2>&1 | grep "API Key for testing" | awk '{print $NF}')
if [ -n "$API_KEY" ]; then
    echo "=== API Key para pruebas: $API_KEY ==="
    echo "Guarde esta clave en un lugar seguro, la necesitará para acceder a la API."
else
    echo "No se pudo obtener la clave API automáticamente. Espere unos segundos más y consulte manualmente con:"
    echo "docker logs cloudfaster-api 2>&1 | grep 'API Key for testing'"
fi

# Verificar que todo esté funcionando
echo "Verificando que los contenedores estén funcionando..."
docker ps

echo "=== Configuración completada exitosamente ==="
echo "La API está disponible en http://localhost:8000"
echo "Para acceder a través de Caddy, configure sus servicios con el dominio $DOMAIN_NAME"
echo ""
echo "Puntos de acceso:"
echo "- API URL: http://api.$DOMAIN_NAME (o http://localhost:8000/docs para documentación interactiva)"
echo "- Servicios web: http://[username].$DOMAIN_NAME/[servicio]"
echo "- Filebrowser: http://fb-[username].$DOMAIN_NAME/[servicio]"
echo ""
echo "Para ver los logs:"
echo "- API: docker logs cloudfaster-api"
echo "- MySQL: docker logs cloudfaster-mysql"
echo "- Caddy: docker logs caddy"

# Instrucciones finales
echo ""
echo "=== Próximos pasos ==="
echo "1. Cree un usuario utilizando el endpoint POST /users"
echo "   curl -X POST 'http://localhost:8000/users' -H 'X-API-Key: $API_KEY' -F 'userid=100' -F 'username=ejemplo'"
echo ""
echo "2. Cree servicios para ese usuario utilizando el endpoint POST /service"
echo "   curl -X POST 'http://localhost:8000/service' -H 'X-API-Key: $API_KEY' -F 'id_user=100' -F 'tipo_servicio=Static' -F 'nombre_servicio=blog'"
echo ""
echo "3. Para probar rápidamente, ejecute:"
echo "   docker exec -it cloudfaster-api python test_service_blog.py"
