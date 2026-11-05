"""Model management: upload, list, retrieve, delete.

Metadata is persisted as a small JSON sidecar file per model (models/<id>.json)
so the model list survives backend restarts without needing a database.
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.schemas.model import ModelMetadata
from app.services import data_service
from app.services.file_service import ALLOWED_MODEL_EXTENSIONS, FileValidationError, save_upload
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def upload_model(upload: UploadFile) -> ModelMetadata:
    try:
        model_id, path, size = await save_upload(
            upload, settings.models_path, ALLOWED_MODEL_EXTENSIONS, settings.max_model_size_mb
        )
    except FileValidationError as e:
        raise

    meta = ModelMetadata(
        id=model_id,
        filename=upload.filename,
        size=size,
        uploaded_at=datetime.now(timezone.utc),
        status="ready",
    )
    try:
        data_service.save_model(meta.model_dump(mode="json"))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    logger.info("Model uploaded: %s (%s bytes)", meta.filename, size)
    return meta


def list_models() -> list[ModelMetadata]:
    return [ModelMetadata(**metadata) for metadata in data_service.list_models()]


def get_model(model_id: str) -> ModelMetadata | None:
    metadata = data_service.get_model(model_id)
    return ModelMetadata(**metadata) if metadata else None


def get_model_file_path(model_id: str) -> Path | None:
    meta = get_model(model_id)
    if meta is None:
        return None
    suffix = Path(meta.filename).suffix.lower()
    candidate = settings.models_path / f"{model_id}{suffix}"
    return candidate if candidate.exists() else None


def delete_model(model_id: str) -> bool:
    meta = get_model(model_id)
    if meta is None:
        return False
    file_path = get_model_file_path(model_id)
    if not data_service.delete_model(model_id):
        return False
    if file_path and file_path.exists():
        file_path.unlink()
    (settings.models_path / f"{model_id}.json").unlink(missing_ok=True)
    logger.info("Model deleted: %s", model_id)
    return True
