from functools import lru_cache
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps

from app.config import settings
from app.api.auth import require_user
from app.services import inference_service

router = APIRouter(prefix="/api/outputs", tags=["outputs"])


@lru_cache(maxsize=256)
def _make_thumbnail(path: str, modified_ns: int, file_size: int) -> bytes:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail((320, 320), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=78, method=4)
    return buffer.getvalue()


def _thumbnail_response(path: Path) -> Response:
    try:
        file_stat = path.stat()
        thumbnail = _make_thumbnail(str(path), file_stat.st_mtime_ns, file_stat.st_size)
    except (OSError, ValueError):
        raise HTTPException(status_code=415, detail="Could not create an image thumbnail.")
    return Response(
        content=thumbnail,
        media_type="image/webp",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/input/{input_id}")
def get_input(input_id: str, user: dict = Depends(require_user)) -> FileResponse:
    if not input_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid input id.")
    if not inference_service.can_access_asset(input_id, user):
        raise HTTPException(status_code=404, detail="Input image not found.")

    matches = list(settings.uploads_path.glob(f"{input_id}.*"))
    if not matches or not matches[0].is_file():
        raise HTTPException(status_code=404, detail="Input image not found.")

    return FileResponse(matches[0])


@router.get("/thumbnail/input/{input_id}")
def get_input_thumbnail(input_id: str, user: dict = Depends(require_user)) -> Response:
    if not input_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid input id.")
    if not inference_service.can_access_asset(input_id, user):
        raise HTTPException(status_code=404, detail="Input image not found.")

    matches = list(settings.uploads_path.glob(f"{input_id}.*"))
    if not matches or not matches[0].is_file():
        raise HTTPException(status_code=404, detail="Input image not found.")
    return _thumbnail_response(matches[0])


@router.get("/thumbnail/{output_id}")
def get_output_thumbnail(output_id: str, user: dict = Depends(require_user)) -> Response:
    if not output_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid output id.")
    if not inference_service.can_access_asset(output_id, user):
        raise HTTPException(status_code=404, detail="Output not found.")

    path = settings.outputs_path / f"{output_id}.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Output not found.")
    return _thumbnail_response(path)


@router.get("/{output_id}")
def get_output(output_id: str, user: dict = Depends(require_user)) -> FileResponse:
    # output_id is a UUID hex string generated server-side; guard against traversal anyway
    if not output_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid output id.")
    if not inference_service.can_access_asset(output_id, user):
        raise HTTPException(status_code=404, detail="Output not found.")

    path = settings.outputs_path / f"{output_id}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output not found.")

    return FileResponse(path, media_type="image/png", filename=f"{output_id}.png")
