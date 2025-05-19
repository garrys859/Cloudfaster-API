from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from uuid import uuid4
import os
import tempfile
import subprocess

from app.core.config import get_settings
from app.services.docker_service import DockerService
from app.api.auth import get_api_key

router = APIRouter(
    dependencies=[Depends(get_api_key)]
)

settings = get_settings()
docker_service = DockerService()

@router.post("/service", status_code=status.HTTP_201_CREATED)
async def create_service(
    userid: int = Form(...),
    service_type: str = Form(...),
    service_name: str = Form(...),
    file: UploadFile = File(None),
    git_repo_url: str = Form(None)
):
    zip_path = None
    try:
        if file:
            if not file.filename.endswith(".zip"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must be a .zip"
                )
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            temp_file.close()
            with open(temp_file.name, "wb") as f:
                f.write(await file.read())
            zip_path = temp_file.name

        result = docker_service.create_service(
            userid=userid,
            webname=service_name,
            service_type=service_type,
            zip_path=zip_path
        )

        if git_repo_url and git_repo_url.strip():
            try:
                user = docker_service.db_service.get_user_by_userid_or_username(userid, "")
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Username not found for the given user ID"
                    )
                _, username = user
                project_path = f"/srv/users/{username}/{service_name}/data"
                os.makedirs(project_path, exist_ok=True)
                result_clone = subprocess.run(
                    ["git", "clone", git_repo_url, project_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result_clone.returncode != 0:
                    raise Exception(f"Git clone failed: {result_clone.stderr}")
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to clone git repository: {str(e)}"
                )

        return {"status": "Ok"}

    except Exception as e:
        if zip_path and os.path.exists(zip_path):
            os.unlink(zip_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating service: {str(e)}"
        )

@router.get("/service/{service_id}")
async def get_service(service_id: str):
    try:
        query = """
        SELECT ds.userid, ds.webname, ds.webtype_id, ds.status, wt.name as webtype_name
        FROM docker_services ds
        JOIN webtypes wt ON ds.webtype_id = wt.id
        WHERE ds.id = %s
        """
        result = docker_service.db_service.fetch_one(query, (service_id,))
        if not result:
            raise HTTPException(status_code=404, detail="Service not found")
        userid, webname, webtype_id, status, webtype_name = result
        service_create = {
            "userid": userid,
            "service_type": [webtype_name],
            "service_name": webname
        }
        return {
            "service_id": service_id,
            "info": service_create,
            "status": status
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting service: {str(e)}"
        )

@router.post("/control-service/{service_id}/{action}")
async def control_service(service_id: str, action: str):
    try:
        query = """
        SELECT userid, webname
        FROM docker_services
        WHERE id = %s
        """
        result = docker_service.db_service.fetch_one(query, (service_id,))
        if not result:
            raise HTTPException(status_code=404, detail="Service not found")
        userid, webname = result
        docker_service.control_service(userid, webname, action)
        return {"status": "Ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error controlling service: {str(e)}"
        )