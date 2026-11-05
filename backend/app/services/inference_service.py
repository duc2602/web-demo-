"""
Inference job orchestration.

Jobs run in a background thread (via FastAPI's BackgroundTasks) and report
progress into an in-memory JOB_STORE that the GET /api/inference/{job_id}
endpoint polls. This keeps the UI responsive without requiring a task queue
for a local single-user tool.

History is persisted to a JSON file so it survives backend restarts.
"""

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from app.config import settings
from app.inference.model_loader import ModelLoadError
from app.inference.pipeline import InferencePipeline
from app.schemas.inference import InferenceStatusResponse
from app.services import data_service, model_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

_pipeline = InferencePipeline()
_JOB_STORE: dict[str, dict] = {}
_JOB_LOCK = Lock()
_HISTORY_LOCK = Lock()


def _update_job(job_id: str, **fields) -> None:
    with _JOB_LOCK:
        _JOB_STORE[job_id].update(fields)


def get_job(job_id: str) -> Optional[dict]:
    with _JOB_LOCK:
        job = _JOB_STORE.get(job_id)
        return dict(job) if job else None


def _append_history(record: dict) -> None:
    with _HISTORY_LOCK:
        data_service.append_history(record)


def get_history(user: dict) -> list[dict]:
    with _HISTORY_LOCK:
        history = [item for item in _read_history() if not item.get("deleted_at")]
        return history if user["role"] == "admin" else [item for item in history if item.get("owner_id") == user["id"]]


def get_trash(user: dict) -> list[dict]:
    with _HISTORY_LOCK:
        history = [item for item in _read_history() if item.get("deleted_at")]
        return history if user["role"] == "admin" else [item for item in history if item.get("owner_id") == user["id"]]


def _read_history() -> list[dict]:
    return data_service.list_history()


def _can_access_record(record: dict, user: dict) -> bool:
    return user["role"] == "admin" or record.get("owner_id") == user["id"]


def move_history_to_trash(job_id: str, user: dict) -> bool:
    with _HISTORY_LOCK:
        history = _read_history()
        record = next((item for item in history if item.get("job_id") == job_id), None)
        if record is None or record.get("deleted_at") or not _can_access_record(record, user):
            return False

        deleted_at = datetime.now(timezone.utc).isoformat()
        return data_service.set_history_deleted_at(job_id, deleted_at)


def restore_history_record(job_id: str, user: dict) -> bool:
    with _HISTORY_LOCK:
        history = _read_history()
        record = next((item for item in history if item.get("job_id") == job_id), None)
        if record is None or not record.get("deleted_at") or not _can_access_record(record, user):
            return False

        return data_service.set_history_deleted_at(job_id, None)


def permanently_delete_history_record(job_id: str, user: dict) -> bool:
    with _HISTORY_LOCK:
        history = _read_history()
        record = next((item for item in history if item.get("job_id") == job_id), None)
        if record is None or not record.get("deleted_at") or not _can_access_record(record, user):
            return False

        if not data_service.permanently_delete_history(job_id):
            return False

    _delete_record_images(record)
    return True


def can_access_asset(asset_id: str, user: dict) -> bool:
    if user["role"] == "admin":
        return True
    return data_service.user_owns_asset(asset_id, user["id"])


def _delete_record_images(record: dict) -> None:
    file_ids = (
        record.get("output_id"),
        record.get("degraded_id"),
        *(record.get("output_ids") or []),
        *(record.get("degraded_ids") or []),
    )
    for file_id in set(file_ids):
        if isinstance(file_id, str) and file_id.isalnum():
            try:
                (settings.outputs_path / f"{file_id}.png").unlink(missing_ok=True)
            except OSError as error:
                logger.warning("Could not remove output image %s: %s", file_id, error)

    input_id = record.get("input_id")
    if isinstance(input_id, str) and input_id.isalnum():
        for path in settings.uploads_path.glob(f"{input_id}.*"):
            try:
                path.unlink(missing_ok=True)
            except OSError as error:
                logger.warning("Could not remove input image %s: %s", input_id, error)


def create_job(model_id: str, input_filename: str, input_path: Path, owner_id: str) -> str:
    job_id = uuid.uuid4().hex
    with _JOB_LOCK:
        _JOB_STORE[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "processed_tiles": 0,
            "total_tiles": 0,
            "elapsed_seconds": 0.0,
            "error": None,
            "input": None,
            "output": None,
            "tiles": None,
            "output_url": None,
            "degraded_url": None,
            "pages": [],
            "processing_time_seconds": None,
            "metrics": None,
            "model_id": model_id,
            "owner_id": owner_id,
            "input_filename": input_filename,
            "input_path": str(input_path),
        }
    return job_id


def run_job(
    job_id: str,
    tile_size: int,
    tile_overlap: int,
    batch_size: int,
    device: str,
    processing_mode: str,
    degradation_mode: str = "direct",
    noise_sigma: float = 25.0,
    degradation_strength: int = 25,
    owner_id: str | None = None,
) -> None:
    """Executes synchronously - call this from a background thread/task."""
    job = get_job(job_id)
    if job is None:
        return

    model_meta = model_service.get_model(job["model_id"])
    model_path = model_service.get_model_file_path(job["model_id"])

    if model_meta is None or model_path is None:
        _update_job(job_id, status="failed", error="Model not found. Please upload a model first.")
        return

    _update_job(job_id, status="loading_model")
    start_time = time.time()

    def on_progress(processed: int, total: int) -> None:
        pct = int((processed / total) * 100) if total else 0
        _update_job(
            job_id,
            status="processing",
            processed_tiles=processed,
            total_tiles=total,
            progress=pct,
            elapsed_seconds=round(time.time() - start_time, 1),
        )

    output_id = uuid.uuid4().hex
    output_path = settings.outputs_path / f"{output_id}.png"

    degraded_id: Optional[str] = None
    degraded_path: Optional[Path] = None
    if degradation_mode != "direct":
        degraded_id = uuid.uuid4().hex
        degraded_path = settings.outputs_path / f"{degraded_id}.png"

    try:
        result = _pipeline.run(
            model_path=model_path,
            input_path=Path(job["input_path"]),
            output_path=output_path,
            tile_size=tile_size,
            tile_overlap=tile_overlap,
            batch_size=batch_size,
            device=device,
            processing_mode=processing_mode,
            degradation_mode=degradation_mode,
            noise_sigma=noise_sigma,
            degradation_strength=degradation_strength,
            degraded_output_path=degraded_path,
            on_progress=on_progress,
        )
    except ModelLoadError as e:
        logger.error("Job %s failed (model error): %s", job_id, e)
        _update_job(job_id, status="failed", error=str(e))
        return
    except Exception as e:
        logger.exception("Job %s failed unexpectedly", job_id)
        _update_job(job_id, status="failed", error="Inference failed. Check backend logs for details.")
        return

    elapsed = round(time.time() - start_time, 1)
    _update_job(
        job_id,
        status="completed",
        progress=100,
        input=result["input"],
        output=result["output"],
        tiles=result["tiles"],
        output_url=f"/api/outputs/{output_id}",
        degraded_url=f"/api/outputs/{degraded_id}" if degraded_id else None,
        pages=[
            {
                **page,
                "output_url": f"/api/outputs/{page['output_id']}",
                "degraded_url": f"/api/outputs/{page['degraded_id']}" if page["degraded_id"] else None,
            }
            for page in result["pages"]
        ],
        processing_time_seconds=elapsed,
        metrics=result["metrics"],
    )

    _append_history(
        {
            "job_id": job_id,
            "input_filename": job["input_filename"],
            "model_filename": model_meta.filename,
            "owner_id": job["owner_id"],
            "input_id": Path(job["input_path"]).stem,
            "output_id": output_id,
            "degraded_id": degraded_id,
            "output_ids": [page["output_id"] for page in result["pages"]],
            "degraded_ids": [
                page["degraded_id"] for page in result["pages"] if page["degraded_id"]
            ],
            "degradation_mode": degradation_mode,
            "degradation_strength": degradation_strength,
            "status": "completed",
            "processing_time_seconds": elapsed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    logger.info("Job %s completed in %.1fs", job_id, elapsed)


def to_status_response(job: dict) -> InferenceStatusResponse:
    return InferenceStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        processed_tiles=job["processed_tiles"],
        total_tiles=job["total_tiles"],
        elapsed_seconds=job["elapsed_seconds"],
        error=job["error"],
        input=job["input"],
        output=job["output"],
        tiles=job["tiles"],
        output_url=job["output_url"],
        degraded_url=job["degraded_url"],
        pages=job["pages"],
        processing_time_seconds=job["processing_time_seconds"],
        metrics=job["metrics"],
    )