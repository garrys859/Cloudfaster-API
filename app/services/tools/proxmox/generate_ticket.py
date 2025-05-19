#!/usr/bin/env python3
import requests
import json
from urllib.parse import quote_plus
import warnings
import sys

from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

HOST    = "https://novnc.cloudfaster.app"
USER    = "root@pam"
PASSWORD= "cRoTa@123"
NODE    = "sv2"

if len(sys.argv) > 1:
    try:
        VMID = int(sys.argv[1])
    except Exception:
        print(json.dumps({"error": "Invalid VMID", "status": "invalid_vmid"}))
        sys.exit(1)
else:
    VMID = 0

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
    resp.raise_for_status() # Lanza una excepcion si la peticion falla (ej. credenciales incorrectas)
    data = resp.json()["data"]
    ticket = data["ticket"]
    csrf   = data["CSRFPreventionToken"]
    session.cookies.set("PVEAuthCookie", ticket, domain=HOST.split('//')[1].split(':')[0], path="/")

    return ticket, csrf


def get_vnc_proxy(csrf_token):
    """
    Request VNC proxy ticket and port for NoVNC.
    Esta peticion ahora deberia incluir la PVEAuthCookie establecida por get_pve_credentials.
    """
    resp = session.post(
        f"{HOST}/api2/json/nodes/{NODE}/lxc/{VMID}/vncproxy",
        params={"websocket": 1},
        headers={"CSRFPreventionToken": csrf_token} # CSRF es necesario ademas de la cookie de sesion
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
        # 1. Obtener credenciales y establecer PVEAuthCookie en la SESIoN DE PYTHON
        session_ticket_value, csrf_token_value = get_pve_credentials()

        # 2. Obtener VNC proxy usando la sesion autenticada
        vnc_ticket_value, vnc_port_value = get_vnc_proxy(csrf_token_value)

        # 3. Construir URL
        novnc_url_value = build_novnc_url(session_ticket_value, vnc_ticket_value, vnc_port_value)

        print(json.dumps({
            "PVEAuthCookie": session_ticket_value, # Para PHP y el navegador del cliente
            "vnc_ticket":    vnc_ticket_value,
            "vnc_port":      vnc_port_value,
            "novnc_url":     novnc_url_value
        }))

    except requests.exceptions.HTTPError as e:
        # Captura errores HTTP especificos, como el 401
        error_message = f"API Proxmox error: {e.response.status_code} {e.response.reason}"
        try:
            # Intentar obtener mas detalles del cuerpo de la respuesta si es JSON
            error_details = e.response.json()
            error_message += f" - Details: {json.dumps(error_details)}"
        except json.JSONDecodeError:
            error_message += f" - Body answer (no JSON): {e.response.text}"
        print(json.dumps({"error": error_message, "status": "python_http_error"}))

    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"Connection error: {str(e)}", "status": "python_connection_error"}))
    except Exception as e:
        print(json.dumps({"error": f"Error: {str(e)}", "status": "python_generic_error"}))
