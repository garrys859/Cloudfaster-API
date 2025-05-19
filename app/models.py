from pydantic import BaseModel, Field
from typing import Optional, List

class OS(str):
    WINDOWS_11 = "WINDOWS_11"
    WINDOWS_SERVER_2025 = "WINDOWS_SERVER_2025"
    WINDOWS_SERVER_2022 = "WINDOWS_SERVER_2022"
    UBUNTU24_CLIENT = "UBUNTU24_CLIENT"
    UBUNTU24_SERVER = "UBUNTU24_SERVER"
    FEDORA = "FEDORA"
    REDHAT = "REDHAT 9.5"

class VMAction(str):
    SHUTDOWN = "shutdown"
    PAUSE = "pause"
    START = "start"
    DELETE = "delete"

class ServiceAction(str):
    SHUTDOWN = "shutdown"
    RESTART = "restart"
    START = "start"
    DELETE = "delete"

class VMCreate(BaseModel):
    userid: str
    vm_name: str
    os: str
    disksize: int = Field(40, ge=10, le=500)
    cores: int = Field(2, ge=1, le=8)
    memory: int = Field(2048, ge=200, le=16384)
    ssh_pub_key: Optional[str] = None

class VM(BaseModel):
    vm_id: str
    info: VMCreate
    status: str = "active"

class ServiceCreate(BaseModel):
    userid: int
    service_type: List[str]
    service_name: str

class Service(BaseModel):
    service_id: str
    info: ServiceCreate
    status: str = "active"

TEMPLATE_IDS = {
    OS.WINDOWS_11: 202,
    OS.WINDOWS_SERVER_2025: 103,
    OS.WINDOWS_SERVER_2022: 201,
    OS.UBUNTU24_CLIENT: 204,
    OS.UBUNTU24_SERVER: 203,
    OS.FEDORA: 106,
    OS.REDHAT: 107
}