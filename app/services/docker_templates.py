DOCKER_TEMPLATES = {
    "Static": """
services:
  {username}-{webname}:
    image: httpd:alpine
    container_name: {username}-{webname}
    volumes:
      - ./data:/usr/local/apache2/htdocs
    networks: [caddy_net]
    labels:
      caddy: {username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}:80"
    restart: always

  {username}-{webname}-fb:
    image: filebrowser/filebrowser:latest
    container_name: {username}-{webname}-fb
    volumes:
      - ./filebrowser_data/filebrowser.db:/database.db
      - ./data:/srv
    command: --database /database.db --baseurl "/{webname}" --root "/srv"
    networks: [caddy_net]
    labels:
      caddy: fb-{username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}-fb:80"
    restart: always

networks:
  caddy_net:
    external: true
""",
    "PHP": """
services:
  {username}-{webname}:
    image: php:8.2-apache
    container_name: {username}-{webname}
    volumes:
      - ./data:/var/www/html
    networks: [caddy_net]
    labels:
      caddy: {username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}:80"
    restart: always

  {username}-{webname}-fb:
    image: filebrowser/filebrowser:latest
    container_name: {username}-{webname}-fb
    volumes:
      - ./filebrowser_data/filebrowser.db:/database.db
      - ./data:/srv
    command: --database /database.db --baseurl "/{webname}" --root "/srv"
    networks: [caddy_net]
    labels:
      caddy: fb-{username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}-fb:80"
    restart: always

networks:
  caddy_net:
    external: true
""",
    "Laravel": """
services:
  {username}-{webname}:
    image: php:8.2-apache
    container_name: {username}-{webname}
    volumes:
      - ./data:/var/www/html/{webname}
      - ./scripts:/scripts
    environment:
      - APACHE_DOCUMENT_ROOT=/var/www/html/{webname}/public
      - DB_HOST={username}-{webname}-db
      - DB_DATABASE=laravel
      - DB_USERNAME=laravel_user
      - DB_PASSWORD=laravel_password
      - WEB_SUBPATH=/{webname}
      - BASE_URL=https://{username}.lpachristian.com/{webname}
    depends_on:
      - {username}-{webname}-db
    networks: [caddy_net]
    labels:
      caddy: {username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}:80"
    restart: always
    command: ["/scripts/laravel_startup.sh"]

  {username}-{webname}-db:
    image: mysql:8.0
    container_name: {username}-{webname}-db
    volumes:
      - ./db_data:/var/lib/mysql
    environment:
      - MYSQL_DATABASE=laravel
      - MYSQL_ROOT_PASSWORD=laravelpassword
      - MYSQL_USER=laravel_user
      - MYSQL_PASSWORD=laravel_password
    networks: [caddy_net]
    restart: always

  {username}-{webname}-fb:
    image: filebrowser/filebrowser:latest
    container_name: {username}-{webname}-fb
    volumes:
      - ./filebrowser_data/filebrowser.db:/database.db
      - ./data:/srv
    command: --database /database.db --baseurl "/{webname}" --root "/srv"
    networks: [caddy_net]
    labels:
      caddy: fb-{username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}-fb:80"
    restart: always

networks:
  caddy_net:
    external: true
""",
    "Node.js": """
services:
  {username}-{webname}:
    image: node:18-alpine
    container_name: {username}-{webname}
    working_dir: /app
    volumes:
      - ./data:/app
    command: sh -c "npm install && npm start"
    networks: [caddy_net]
    labels:
      caddy: {username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}:3000"
    restart: always

  {username}-{webname}-fb:
    image: filebrowser/filebrowser:latest
    container_name: {username}-{webname}-fb
    volumes:
      - ./filebrowser_data/filebrowser.db:/database.db
      - ./data:/srv
    command: --database /database.db --baseurl "/{webname}" --root "/srv"
    networks: [caddy_net]
    labels:
      caddy: fb-{username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}-fb:80"
    restart: always

networks:
  caddy_net:
    external: true
""",
    "Python": """
services:
  {username}-{webname}:
    image: python:3.10-slim
    container_name: {username}-{webname}
    working_dir: /app
    volumes:
      - ./data:/app
    command: sh -c "pip install -r requirements.txt && python main.py"
    networks: [caddy_net]
    labels:
      caddy: {username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}:8000"
    restart: always

  {username}-{webname}-fb:
    image: filebrowser/filebrowser:latest
    container_name: {username}-{webname}-fb
    volumes:
      - ./filebrowser_data/filebrowser.db:/database.db
      - ./data:/srv
    command: --database /database.db --baseurl "/{webname}" --root "/srv"
    networks: [caddy_net]
    labels:
      caddy: fb-{username}.lpachristian.com
      caddy.01_redir: "/{webname} /{webname}/ 308"
      caddy.02_handle_path: "/{webname}/*"
      caddy.02_handle_path.reverse_proxy: "{username}-{webname}-fb:80"
    restart: always

networks:
  caddy_net:
    external: true
"""
}