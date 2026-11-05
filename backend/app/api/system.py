import platform

import psutil
from fastapi import APIRouter, Depends

from app.api.auth import require_user
from app.schemas.system import SystemInfo

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("", response_model=SystemInfo)
def get_system_info(_user: dict = Depends(require_user)) -> SystemInfo:
    import torch

    cuda_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if cuda_available else None
    ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)

    return SystemInfo(
        device="cuda" if cuda_available else "cpu",
        cuda_available=cuda_available,
        gpu_name=gpu_name,
        cpu=platform.processor() or platform.machine() or "unknown",
        ram_gb=ram_gb,
    )
