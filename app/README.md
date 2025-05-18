# CloudFaster API

API para gestionar servicios Docker y máquinas virtuales de Proxmox.

## Requisitos

- Docker
- Docker Compose

## Instalación y ejecución

1. Clonar el repositorio
2. Navegar a la carpeta del proyecto
3. Ejecutar Docker Compose:

```bash
docker-compose up -d
```

El sistema realizará automáticamente lo siguiente:
- Levantar una base de datos MySQL
- Inicializar la base de datos con las tablas necesarias
- Crear un usuario admin y una clave API inicial
- Mostrar la clave API generada en los logs de la aplicación

## Acceso a la API

La API estará disponible en: http://localhost:8000

### Endpoints principales:

- `/` - Bienvenida
- `/heartbeat` - Comprobar estado
- `/protected` - Endpoint protegido (requiere API key)
- `/docs` - Documentación Swagger

## Obtener la clave API

Puedes ver la clave API generada ejecutando:

```bash
docker logs cloudfaster-api | grep "API Key"
```

Esta clave API es necesaria para acceder a los endpoints protegidos.

## Solución de problemas

Si encuentras el error `ModuleNotFoundError: No module named 'app'`, se debe a la estructura de importaciones. Se ha corregido este problema modificando las importaciones en los archivos `main.py`, `core/db.py`, `core/db_init.py` y `entrypoint.sh` para no depender del paquete `app`. 