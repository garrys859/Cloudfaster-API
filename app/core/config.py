from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_USER: str = os.getenv("DB_USER", "cloudfaster")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "qwerty-1234")
    DB_NAME: str = os.getenv("DB_NAME", "cloudfaster")
    PROXMOX_HOST: str = os.getenv("PROXMOX_HOST", "192.168.1.241")
    PROXMOX_USER: str = os.getenv("PROXMOX_USER", "root@pam")
    PROXMOX_PASSWORD: str = os.getenv("PROXMOX_PASSWORD", "cRoTa@123")
    PROXMOX_VERIFY_SSL: bool = False
    DOCKER_BASE_PATH: str = os.getenv("DOCKER_BASE_PATH", "/srv")
    API_TITLE: str = "Cloudfaster API"
    API_DESCRIPTION: str = "API for managing VMs and Docker services"
    API_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()