from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Response, UploadFile

from app.config import settings
from app.api.auth import require_admin, require_user
from app.schemas.inference import HistoryRecord, InferenceCreateResponse, InferenceStatusResponse
from app.services import inference_service, model_service
from app.services.file_service import ALLOWED_IMAGE_EXTENSIONS, FileValidationError, save_upload

router = APIRouter(prefix="/api/inference", tags=["inference"])


@router.post("", response_model=InferenceCreateResponse)
async def start_inference(
    background_tasks: BackgroundTasks,
    selected_id: str = Form(..., alias="model_id"),
    input_image: UploadFile = None,
    tile_size: int = Form(default=settings.default_tile_size),
    tile_overlap: int = Form(default=settings.default_tile_overlap),
    batch_size: int = Form(default=settings.default_batch_size),
    device: str = Form(default=settings.default_device),
    processing_mode: str = Form(default=settings.default_processing_mode),
    degradation_mode: str = Form(default="direct"),
    noise_sigma: float = Form(default=25.0),
    degradation_strength: int = Form(default=25),
    user: dict = Depends(require_user),
) -> InferenceCreateResponse:
    if model_service.get_model(selected_id) is None:
        raise HTTPException(status_code=400, detail="Please upload a model first.")

    if input_image is None:
        raise HTTPException(status_code=400, detail="Please select an input image.")
    if tile_size < 32 or tile_size % 8 != 0:
        raise HTTPException(status_code=400, detail="Tile size must be a multiple of 8 and at least 32.")
    if tile_overlap < 0 or tile_overlap >= tile_size:
        raise HTTPException(status_code=400, detail="Tile overlap must be 0 or more and smaller than tile size.")
    if batch_size < 1 or batch_size > 64:
        raise HTTPException(status_code=400, detail="Batch size must be between 1 and 64.")
    if device not in ("auto", "cpu", "cuda"):
        raise HTTPException(status_code=400, detail="Device must be auto, cpu or cuda.")
    if processing_mode not in ("tile", "full_image"):
        raise HTTPException(status_code=400, detail="Processing mode must be tile or full_image.")
    if degradation_mode not in ("direct", "synthetic_noise", "blur", "broken", "missing", "occlusion"):
        raise HTTPException(status_code=400, detail="Invalid degradation mode.")
    if degradation_mode == "synthetic_noise" and not (0 < noise_sigma <= 100):
        raise HTTPException(status_code=400, detail="Noise sigma must be greater than 0 and at most 100.")
    if degradation_mode not in ("direct", "synthetic_noise") and not (1 <= degradation_strength <= 100):
        raise HTTPException(status_code=400, detail="Degradation strength must be between 1 and 100.")

    try:
        _, saved_path, _ = await save_upload(
            input_image, settings.uploads_path, ALLOWED_IMAGE_EXTENSIONS, settings.max_image_size_mb
        )
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = inference_service.create_job(selected_id, input_image.filename, saved_path, user["id"])

    background_tasks.add_task(
        inference_service.run_job,
        job_id=job_id,
        tile_size=tile_size,
        tile_overlap=tile_overlap,
        batch_size=batch_size,
        device=device,
        processing_mode=processing_mode,
        degradation_mode=degradation_mode,
        noise_sigma=noise_sigma,
        degradation_strength=degradation_strength,
        owner_id=user["id"],
    )

    return InferenceCreateResponse(job_id=job_id, status="queued")


@router.get("/history", response_model=list[HistoryRecord])
def get_history(user: dict = Depends(require_user)) -> list[HistoryRecord]:
    return [HistoryRecord(**r) for r in inference_service.get_history(user)]


@router.get("/trash", response_model=list[HistoryRecord])
def get_trash(user: dict = Depends(require_user)) -> list[HistoryRecord]:
    return [HistoryRecord(**r) for r in inference_service.get_trash(user)]


@router.delete("/history/{job_id}", status_code=204)
def delete_history_record(job_id: str, user: dict = Depends(require_user)) -> Response:
    if not inference_service.move_history_to_trash(job_id, user):
        raise HTTPException(status_code=404, detail="History record not found.")
    return Response(status_code=204)


@router.post("/trash/{job_id}/restore", status_code=204)
def restore_history_record(job_id: str, user: dict = Depends(require_user)) -> Response:
    if not inference_service.restore_history_record(job_id, user):
        raise HTTPException(status_code=404, detail="Trashed history record not found.")
    return Response(status_code=204)


@router.delete("/trash/{job_id}", status_code=204)
def permanently_delete_history_record(job_id: str, user: dict = Depends(require_admin)) -> Response:
    if not inference_service.permanently_delete_history_record(job_id, user):
        raise HTTPException(status_code=404, detail="Trashed history record not found.")
    return Response(status_code=204)


@router.get("/{job_id}", response_model=InferenceStatusResponse)
def get_inference_status(job_id: str, user: dict = Depends(require_user)) -> InferenceStatusResponse:
    job = inference_service.get_job(job_id)
    if job is None or (user["role"] != "admin" and job.get("owner_id") != user["id"]):
        raise HTTPException(status_code=404, detail="Job not found.")
    return inference_service.to_status_response(job)
