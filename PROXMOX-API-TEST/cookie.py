# generate_ticket.py
#!/usr/bin/env python3
import requests
import json
from urllib.parse import quote_plus

# === Configuración ===
HOST    = "https://119.12.242.157:8006"
USER    = "root@pam"
PASSWORD= "Xugvzkm05."
NODE    = "jormundongor"
VMID    = 9038

session = requests.Session()
session.verify = False  # Deshabilitar verificación SSL si no hay cert válido

def get_pve_credentials():
    """
    Log in to Proxmox, return session ticket and CSRF token, and inject cookie.
    """
    resp = session.post(
        f"{HOST}/api2/json/access/ticket",
        data={"username": USER, "password": PASSWORD}
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    ticket = data["ticket"]
    csrf   = data["CSRFPreventionToken"]
    session.cookies.set("PVEAuthCookie", ticket)
    return ticket, csrf


def get_vnc_proxy(csrf_token):
    """
    Request VNC proxy ticket and port for NoVNC.
    """
    resp = session.post(
        f"{HOST}/api2/json/nodes/{NODE}/qemu/{VMID}/vncproxy",
        params={"websocket": 1},
        headers={"CSRFPreventionToken": csrf_token}
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return data["ticket"], data["port"]


def build_novnc_url(ticket, vnc_ticket, vnc_port):
    """
    Build the full NoVNC URL with token and encoded path.
    """
    raw_path = (
        f"api2/json/nodes/{NODE}/qemu/{VMID}/vncwebsocket"
        f"?port={vnc_port}&vncticket={vnc_ticket}"
    )
    enc_path = quote_plus(raw_path)
    enc_token= quote_plus(ticket)
    return (
        f"{HOST}/?token={enc_token}"
        f"&console=kvm&novnc=1"
        f"&node={NODE}&vmid={VMID}"
        f"&path={enc_path}"
    )


if __name__ == "__main__":
    session_ticket, csrf_token = get_pve_credentials()
    vnc_ticket, vnc_port      = get_vnc_proxy(csrf_token)
    novnc_url                  = build_novnc_url(session_ticket, vnc_ticket, vnc_port)

    # Output JSON for PHP script
    print(json.dumps({
        "session_ticket": session_ticket,
        "vnc_ticket":    vnc_ticket,
        "vnc_port":      vnc_port,
        "novnc_url":     novnc_url
    }))