# Caddy Proxy Dinámico

Este proyecto configura Caddy como proxy inverso para servicios Docker con enrutamiento basado en subdominios y rutas.

## Cómo funciona

La configuración de Caddy utiliza un patrón de enrutamiento de la forma:
```
{nombre}.lpachristian.com/{servicio}
```

Donde:
- `{nombre}` es el subdominio que identifica al usuario o entorno
- `{servicio}` es el nombre del servicio específico

Caddy enruta estas solicitudes automáticamente al contenedor Docker llamado `{nombre}-{servicio}`.

## Ejemplos de uso

### Ejemplo 1: Juan con servicio "primo"

Para un servicio accesible en `juan.lpachristian.com/primo`, necesitas crear un contenedor Docker llamado `juan-primo`.

```yaml
# juan-primo-service.yml
services:
  juan-primo:
    image: nginx:alpine
    container_name: juan-primo
    volumes:
      - ./primo:/usr/share/nginx/html
    networks: [caddy_net]
    labels:
      caddy: primo.lpachristian.com
      caddy.01_redir: "/juan /juan/ 308"
      caddy.02_handle_path: "/juan/*"
      caddy.02_handle_path.reverse_proxy: "juan-primo:80"
networks:
  caddy_net:
    external: true
```

## Instrucciones de implementación

1. Despliega Caddy con el docker-compose principal
2. Crea redes Docker compartidas para que los contenedores se comuniquen
3. Despliega tus servicios siguiendo la convención de nombres `{nombre}-{servicio}`
4. Accede a tus servicios mediante `{nombre}.lpachristian.com/{servicio}`

## Depuración

Si tienes problemas, revisa las cabeceras de depuración que Caddy añade a las respuestas:
- `debug-host`: El host solicitado
- `debug-uri`: La URI completa solicitada
- `debug-labels`: El subdominio extraído
- `debug-path`: La primera parte de la ruta extraída 