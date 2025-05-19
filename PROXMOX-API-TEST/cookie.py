#!/usr/bin/env python3
import requests
import json
from urllib.parse import quote_plus
import warnings

from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# === Configuración ===
HOST    = "https://192.168.1.241:8006"
USER    = "root@pam"
PASSWORD= "cRoTa@123" # ¡INSEGURO!
NODE    = "sv1"
VMID    = 108

session = requests.Session()
session.verify = False

def get_pve_credentials():
    """
    Log in to Proxmox, return session ticket and CSRF token, and inject cookie INTO PYTHON'S SESSION.
    """
    resp = session.post(
        f"{HOST}/api2/json/access/ticket",
        data={"username": USER, "password": PASSWORD}
    )
    resp.raise_for_status() # Lanza una excepción si la petición falla (ej. credenciales incorrectas)
    data = resp.json()["data"]
    ticket = data["ticket"]
    csrf   = data["CSRFPreventionToken"]

    # --- IMPORTANTE: Añadir la cookie a la sesión de Python ---
    # Esta cookie se usará para las siguientes peticiones DENTRO de este script de Python.
    # El nombre de la cookie debe ser exactamente "PVEAuthCookie".
    # El `domain` y `path` aquí son para la sesión de `requests`, Proxmox los manejará
    # correctamente en su respuesta si los necesita.
    session.cookies.set("PVEAuthCookie", ticket, domain=HOST.split('//')[1].split(':')[0], path="/")
    # --- FIN IMPORTANTE ---

    return ticket, csrf


def get_vnc_proxy(csrf_token):
    """
    Request VNC proxy ticket and port for NoVNC.
    Esta petición ahora debería incluir la PVEAuthCookie establecida por get_pve_credentials.
    """
    resp = session.post(
        f"{HOST}/api2/json/nodes/{NODE}/qemu/{VMID}/vncproxy",
        params={"websocket": 1},
        headers={"CSRFPreventionToken": csrf_token} # CSRF es necesario además de la cookie de sesión
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return data["ticket"], data["port"]


def build_novnc_url(session_ticket_val, vnc_ticket, vnc_port):
    raw_path = (
        f"api2/json/nodes/{NODE}/qemu/{VMID}/vncwebsocket"
        f"?port={vnc_port}&vncticket={vnc_ticket}"
    )
    enc_path = quote_plus(raw_path)
    enc_session_token = quote_plus(session_ticket_val)
    return (
        f"{HOST}/?token={enc_session_token}"
        f"&console=kvm&novnc=1"
        f"&node={NODE}&vmid={VMID}"
        f"&path={enc_path}"
    )


if __name__ == "__main__":
    try:
        # 1. Obtener credenciales y establecer PVEAuthCookie en la SESIÓN DE PYTHON
        session_ticket_value, csrf_token_value = get_pve_credentials()

        # 2. Obtener VNC proxy usando la sesión autenticada
        vnc_ticket_value, vnc_port_value = get_vnc_proxy(csrf_token_value)

        # 3. Construir URL
        novnc_url_value = build_novnc_url(session_ticket_value, vnc_ticket_value, vnc_port_value)

        print(json.dumps({
            "session_ticket": session_ticket_value, # Para PHP y el navegador del cliente
            "vnc_ticket":    vnc_ticket_value,
            "vnc_port":      vnc_port_value,
            "novnc_url":     novnc_url_value
        }))

    except requests.exceptions.HTTPError as e:
        # Captura errores HTTP específicos, como el 401
        error_message = f"Error de API Proxmox: {e.response.status_code} {e.response.reason}"
        try:
            # Intentar obtener más detalles del cuerpo de la respuesta si es JSON
            error_details = e.response.json()
            error_message += f" - Detalles: {json.dumps(error_details)}"
        except json.JSONDecodeError:
            error_message += f" - Cuerpo de respuesta (no JSON): {e.response.text}"
        print(json.dumps({"error": error_message, "status": "python_http_error"}))

    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"Error de conexión: {str(e)}", "status": "python_connection_error"}))
    except Exception as e:
        print(json.dumps({"error": f"Error inesperado en script Python: {str(e)}", "status": "python_generic_error"}))
