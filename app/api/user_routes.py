from fastapi import APIRouter, HTTPException, Depends, Form
from services.db_service import DatabaseService
from api.auth import get_api_key
from core.config import get_settings
import os
import pathlib

router = APIRouter()
settings = get_settings()

db_service = DatabaseService(
    host=settings.DB_HOST,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    database=settings.DB_NAME
)

# Directorio base para las carpetas de usuarios
USER_BASE_DIR = pathlib.Path(settings.USER_BASE_PATH)

@router.post("/users")
async def create_user(
    userid: int = Form(...),
    username: str = Form(...),
    api_key: str = Depends(get_api_key)
):
    existing = db_service.get_user_by_userid_or_username(userid, username)
    if existing:
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    
    # Crear usuario en la base de datos
    db_service.create_user(userid, username)
    
    # Crear carpeta para el usuario
    try:
        user_dir = USER_BASE_DIR / username
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Establecer permisos adecuados
        os.chmod(user_dir, 0o755)  # rwxr-xr-x
        
        return {
            "status": "success",
            "message": "Usuario creado correctamente",
            "userid": userid,
            "username": username,
            "user_directory": str(user_dir)
        }
    except Exception as e:
        # Si hay un error al crear la carpeta, informar pero no fallar
        # Ya que el usuario ya se creó en la base de datos
        return {
            "status": "partial_success",
            "message": f"Usuario creado en la base de datos, pero hubo un error al crear su directorio: {str(e)}",
            "userid": userid,
            "username": username
        }

@router.get("/users/{userid}")
async def get_user(userid: str, api_key: str = Depends(get_api_key)):
    user = db_service.get_user_by_userid(userid)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user_id, username, created_at = user
    services = db_service.get_services_by_userid(userid)
    vms = db_service.get_vms_by_userid(userid)
    return {
        "userid": user_id,
        "username": username,
        "created_at": created_at,
        "services": services,
        "vms": vms
    }