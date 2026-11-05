from fastapi import APIRouter, HTTPException, UploadFile
from fastapi import Depends

from app.api.auth import require_admin, require_user
from app.schemas.model import ModelDeleteResponse, ModelListResponse, ModelMetadata
from app.services import model_service
from app.services.file_service import FileValidationError

router = APIRouter(prefix="/api/models", tags=["models"])


@router.post("/upload", response_model=ModelMetadata)
async def upload_model(file: UploadFile, _admin: dict = Depends(require_admin)) -> ModelMetadata:
    try:
        return await model_service.upload_model(file)
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ModelListResponse)
def list_models(_user: dict = Depends(require_user)) -> ModelListResponse:
    return ModelListResponse(models=model_service.list_models())


@router.get("/{model_id}", response_model=ModelMetadata)
def get_model(model_id: str, _user: dict = Depends(require_user)) -> ModelMetadata:
    meta = model_service.get_model(model_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Model not found.")
    return meta


@router.delete("/{model_id}", response_model=ModelDeleteResponse)
def delete_model(model_id: str, _admin: dict = Depends(require_admin)) -> ModelDeleteResponse:
    deleted = model_service.delete_model(model_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Model not found.")
    return ModelDeleteResponse(id=model_id, deleted=True)
