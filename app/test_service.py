#!/usr/bin/env python3
from services.docker_service import DockerService
import traceback
import sys

def main():
    try:
        # Inicializar el servicio Docker
        docker_service = DockerService()
        
        # Parámetros para crear un servicio
        userid = 11  # Usar el ID del usuario 'christian'
        webname = "test2"  # Nombre del servicio
        tipo_servicio = "Static"  # Tipo de servicio (debe existir en DOCKER_TEMPLATES)
        
        print(f"Creando servicio '{webname}' para el usuario con ID {userid}...")
        
        # Intentar crear el servicio
        result = docker_service.create_service(userid, webname, tipo_servicio)
        
        # Mostrar el resultado
        print("Resultado:", result)
        
    except Exception as e:
        print(f"Error: {e}")
        print("Traceback:")
        traceback.print_exc(file=sys.stdout)

if __name__ == "__main__":
    main() 