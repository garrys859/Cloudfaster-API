from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import JSONResponse
from typing import Optional
import subprocess
import json

from app.core.config import get_settings
from app.api.auth import get_api_key
from app.services.proxmox_service import ProxmoxService
from app.models import OS, VMAction, VMCreate, VM, TEMPLATE_IDS

router = APIRouter(
    dependencies=[Depends(get_api_key)]
)

settings = get_settings()

@router.get("/vm/{vm_id}", response_model=VM)
async def get_vm(vm_id: str):
    try:
        proxmox_service = ProxmoxService()
        query = """
        SELECT userid, vm_name, os, status
        FROM proxmox_vms
        WHERE vm_id = %s
        """
        result = proxmox_service.db_service.fetch_one(query, (vm_id,))
        if not result:
            raise HTTPException(status_code=404, detail="VM not found")
        userid, vm_name, os, status = result
        vm_create = VMCreate(
            userid=userid,
            os=os,
            vm_name=vm_name,
            disksize=40,
            cores=2,
            memory=2048,
            ssh_pub_key=None
        )
        return VM(vm_id=vm_id, info=vm_create, status=status)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting VM: {str(e)}"
        )

@router.post("/vm", response_model=VM, status_code=status.HTTP_201_CREATED)
async def create_vm(
    userid: int = Form(...),
    vm_name: str = Form(...),
    os: str = Form(...),
    disksize: int = Form(40),
    cores: int = Form(2),
    memory: int = Form(2048),
    ssh_pub_key: Optional[str] = Form(None)
):
    vm_data = VMCreate(
        userid=str(userid),
        vm_name=vm_name,
        os=os,
        disksize=disksize,
        cores=cores,
        memory=memory,
        ssh_pub_key=ssh_pub_key
    )
    proxmox_service = ProxmoxService()
    template_id = TEMPLATE_IDS.get(os, 103)
    result = proxmox_service.clone_vm_atomic(
        userid=userid,
        node="sv4",
        template_id=template_id,
        vm_name=vm_name,
        os=os,
        cores=cores,
        memory=memory,
        ssh_pub_key=ssh_pub_key,
        template_node="sv1"
    )
    if result["status"] != "success":
        raise HTTPException(status_code=500, detail=result["message"])
    return {"status": "Ok"}

@router.post("/vm/connect/{vm_id}")
async def generate_ticket(vm_id: int):
    if not vm_id:
        raise HTTPException(
            status_code=400,
            detail="vm_id is required"
        )
    script_path = "/root/CloudFasterMAIN/app/services/tools/proxmox/generate_ticket.py"
    try:
        result = subprocess.run(
            ["python3", script_path, str(vm_id)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            output = json.loads(result.stdout.strip())
        except Exception:
            output = {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        return JSONResponse(
            status_code=200,
            content=output
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing script: {str(e)}"
        )

@router.post("/control-vm/{vm_id}/{action}")
async def control_vm(vm_id: str, action: str):
    try:
        clean_vm_id = vm_id.strip()
        if not clean_vm_id.isdigit():
            raise HTTPException(
                status_code=400,
                detail="VM ID must be a valid integer."
            )
        proxmox_service = ProxmoxService()
        nodes = ["sv4", "sv5"]
        last_error = None
        for node in nodes:
            try:
                result = proxmox_service.control_vm(int(clean_vm_id), action, node=node)
                if result["status"] == "success":
                    return {"status": "Ok"}
                else:
                    last_error = result.get("message", "Unknown error")
                if "does not exist" in last_error or "not found" in last_error:
                    continue
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=last_error
                    )
            except Exception as e:
                last_error = str(e)
                if "does not exist" in last_error or "not found" in last_error:
                    continue
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=last_error
                    )
        raise HTTPException(
            status_code=404,
            detail=f"VM {clean_vm_id} not found in any node (sv4, sv5)"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error controlling VM: {str(e)}"
        )