from datetime import datetime
from pydantic import BaseModel


class ModelMetadata(BaseModel):
    id: str
    filename: str
    size: int
    uploaded_at: datetime
    status: str  # "ready" | "invalid"


class ModelListResponse(BaseModel):
    models: list[ModelMetadata]


class ModelDeleteResponse(BaseModel):
    id: str
    deleted: bool
