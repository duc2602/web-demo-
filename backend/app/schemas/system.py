from typing import Optional
from pydantic import BaseModel


class SystemInfo(BaseModel):
    device: str
    cuda_available: bool
    gpu_name: Optional[str] = None
    cpu: str
    ram_gb: float
