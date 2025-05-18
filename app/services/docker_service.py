import os
import pathlib
import zipfile
import subprocess
import textwrap
import docker
import yaml
from core.config import get_settings
from services.db_service import DatabaseService
from services.docker_templates import DOCKER_TEMPLATES

settings = get_settings()

class DockerService:
    def __init__(self):
        self.user_base_path = pathlib.Path(settings.USER_BASE_PATH)
        self.db_service = DatabaseService(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        self.docker_client = docker.from_env()

    def _ensure_path(self, userid, webname):
        """
        Asegura que exista el directorio para el servicio del usuario.
        Retorna el objeto Path del directorio y el nombre de usuario.
        """
        user_info = self.db_service.get_user_by_userid(userid)
        if not user_info:
            raise ValueError(f"Usuario con ID {userid} no existe. Debe crear el usuario primero.")
        
        username = user_info[1]
        target_dir = self.user_base_path / username / webname
        
        # Crear estructura de directorios
        (target_dir / "data").mkdir(parents=True, exist_ok=True)
        (target_dir / "filebrowser_data").mkdir(exist_ok=True)
        
        return target_dir, username

    def _safe_extract(self, zip_path, dest_path):
        """Extrae un archivo ZIP de manera segura verificando path traversal"""
        with zipfile.ZipFile(zip_path) as zf:
            # Verificar path traversal
            for member in zf.infolist():
                member_path = dest_path / member.filename
                if not str(member_path.resolve()).startswith(str(dest_path.resolve())):
                    raise RuntimeError("Zip traversal detected! Posible intento de ataque.")
            
            # Extraer archivos
            zf.extractall(dest_path)

    def _init_filebrowser(self, target, webname, admin_pass="admin123"):
        """Inicializa el filebrowser para el servicio"""
        filebrowser_db = target / "filebrowser_data" / "filebrowser.db"
        if not filebrowser_db.exists():
            try:
                # Inicializar configuración de filebrowser con Docker Python SDK
                self.docker_client.containers.run(
                    "filebrowser/filebrowser",
                    command=["config", "init", "--database", "/srv/filebrowser.db"],
                    volumes={str(target / 'filebrowser_data'): {'bind': '/srv', 'mode': 'rw'}},
                    remove=True
                )
                
                # Configurar base URL
                self.docker_client.containers.run(
                    "filebrowser/filebrowser",
                    command=["config", "set", "--baseurl", f"/{webname}", "--database", "/srv/filebrowser.db"],
                    volumes={str(target / 'filebrowser_data'): {'bind': '/srv', 'mode': 'rw'}},
                    remove=True
                )
                
                # Crear usuario administrador
                self.docker_client.containers.run(
                    "filebrowser/filebrowser",
                    command=["users", "add", "admin", admin_pass, "--database", "/srv/filebrowser.db", "--perm.admin"],
                    volumes={str(target / 'filebrowser_data'): {'bind': '/srv', 'mode': 'rw'}},
                    remove=True
                )
                
                return True
            except Exception as e:
                print(f"Error inicializando filebrowser: {e}")
                return False
        return True

    def create_service(self, userid, webname, tipo_servicio, zip_path=None, admin_pass="admin123"):
        """
        Crea un nuevo servicio para el usuario.
        
        Args:
            userid: ID del usuario
            webname: Nombre del servicio
            tipo_servicio: Tipo de servicio (debe existir en DOCKER_TEMPLATES)
            zip_path: Ruta al archivo ZIP con el código fuente (opcional)
            admin_pass: Contraseña para el usuario admin de filebrowser
            
        Returns:
            dict: Información sobre el servicio creado
        """
        # Preparar el directorio
        try:
            target_dir, username = self._ensure_path(userid, webname)
            
            # Extraer archivos ZIP si se proporcionaron
            if zip_path:
                self._safe_extract(zip_path, target_dir / "data")
                os.remove(zip_path)  # Limpiar archivo temporal
            
            # Inicializar filebrowser
            self._init_filebrowser(target_dir, webname, admin_pass)
            
            # Obtener la plantilla adecuada
            template = DOCKER_TEMPLATES.get(tipo_servicio)
            if not template:
                raise ValueError(f"Tipo de servicio '{tipo_servicio}' no soportado")
            
            # Generar el docker-compose.yml con los valores del usuario y servicio
            compose_text = template.format(username=username, webname=webname)
            compose_file_path = target_dir / "docker-compose.yml"
            compose_file_path.write_text(compose_text)
            
            print(f"Docker compose file generado en: {compose_file_path}")
            
            # Convertir el YAML a un diccionario para usar con el SDK de Docker
            compose_dict = yaml.safe_load(compose_text)
            
            # Para cada servicio en el docker-compose.yml, crear el contenedor
            for service_name, service_config in compose_dict['services'].items():
                container_name = service_config.get('container_name', service_name)
                
                # Eliminar contenedor si ya existe
                try:
                    existing = self.docker_client.containers.get(container_name)
                    print(f"Eliminando contenedor existente: {container_name}")
                    existing.remove(force=True)
                except docker.errors.NotFound:
                    pass
                
                # Preparar los volúmenes montados
                volumes = {}
                if 'volumes' in service_config:
                    for volume in service_config['volumes']:
                        src, dst = volume.split(':')
                        if src.startswith('./'):
                            src = str(target_dir / src[2:])
                        volumes[src] = {'bind': dst, 'mode': 'rw'}
                
                # Preparar las redes
                networks = []
                if 'networks' in service_config:
                    if isinstance(service_config['networks'], list):
                        networks = service_config['networks']
                    else:
                        networks = list(service_config['networks'].keys())
                
                # Preparar labels
                labels = service_config.get('labels', {})
                
                # Crear el contenedor
                print(f"Creando contenedor: {container_name}")
                environment = service_config.get('environment', {})
                ports = {}
                if 'ports' in service_config:
                    for port_mapping in service_config['ports']:
                        host_port, container_port = port_mapping.split(':')
                        ports[container_port] = host_port
                
                # Comando a ejecutar
                command = service_config.get('command', None)
                
                # Crear y arrancar el contenedor
                self.docker_client.containers.run(
                    service_config['image'],
                    name=container_name,
                    detach=True,
                    volumes=volumes,
                    environment=environment,
                    ports=ports,
                    labels=labels,
                    network=networks[0] if networks else None,
                    command=command,
                    restart_policy={"Name": "always"} if service_config.get('restart') == 'always' else None
                )
            
            # Registrar en la base de datos
            webtype_id = self.db_service.get_webtype_id(tipo_servicio)
            self.db_service.log_docker_service_creation(userid, webname, webtype_id)
            
            # Devolver información del servicio
            return {
                "status": "success",
                "userid": userid,
                "username": username,
                "webname": webname,
                "webtype": tipo_servicio,
                "urls": {
                    "website": f"http://{username}.lpachristian.com/{webname}",
                    "filebrowser": f"http://fb-{username}.lpachristian.com/{webname}"
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error creando servicio: {str(e)}"
            }

    def control_service(self, userid, webname, action):
        """
        Controla un servicio existente (iniciar, detener, reiniciar, eliminar).
        
        Args:
            userid: ID del usuario propietario
            webname: Nombre del servicio
            action: Acción a realizar (encender, apagar, reiniciar, eliminar)
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            target_dir, username = self._ensure_path(userid, webname)
            
            # Leer el archivo docker-compose.yml para obtener los nombres de los contenedores
            compose_file_path = target_dir / "docker-compose.yml"
            if not compose_file_path.exists():
                raise ValueError(f"No existe el archivo docker-compose.yml para el servicio {webname}")
            
            # Obtener los nombres de los contenedores
            compose_dict = yaml.safe_load(compose_file_path.read_text())
            containers = []
            for service_name, service_config in compose_dict['services'].items():
                container_name = service_config.get('container_name', service_name)
                containers.append(container_name)
            
            # Aplicar acción según corresponda
            status = ""
            for container_name in containers:
                try:
                    container = self.docker_client.containers.get(container_name)
                    
                    if action == "encender":
                        container.start()
                        status = "active"
                    elif action == "apagar":
                        container.stop()
                        status = "stopped"
                    elif action == "reiniciar":
                        container.restart()
                        status = "active"
                    elif action == "eliminar":
                        container.remove(force=True)
                        status = "deleted"
                    else:
                        raise ValueError(f"Acción no válida: {action}")
                except docker.errors.NotFound:
                    print(f"Contenedor {container_name} no encontrado")
            
            # Actualizar estado en la base de datos
            result = self.db_service.fetch_one(
                "SELECT id FROM docker_services WHERE userid = %s AND webname = %s",
                (userid, webname)
            )
            if result:
                service_id = result[0]
                self.db_service.update_docker_service_status(service_id, status)
            
            return {
                "status": "success",
                "userid": userid,
                "username": username,
                "webname": webname,
                "action": action,
                "message": f"Operación {action} completada exitosamente"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error controlando servicio: {str(e)}"
            }

    def list_services(self, userid=None, username=None):
        """
        Lista todos los servicios de un usuario o de todos los usuarios.
        
        Args:
            userid: ID del usuario (opcional)
            username: Nombre del usuario (opcional)
            
        Returns:
            list: Lista de servicios
        """
        if userid:
            return self.db_service.get_services_by_userid(userid)
        elif username:
            user = self.db_service.get_user_by_username(username)
            if user:
                return self.db_service.get_services_by_userid(user[0])
            return []
        else:
            # Implementar para listar todos los servicios si es necesario
            pass