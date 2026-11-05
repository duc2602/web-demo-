"""Safe file upload handling: validation, UUID-based storage, no path traversal."""

import uuid
from pathlib import Path

from fastapi import UploadFile

ALLOWED_MODEL_EXTENSIONS = {".pth", ".pt"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


class FileValidationError(Exception):
    pass


def _safe_suffix(filename: str, allowed: set[str]) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        raise FileValidationError(
            f"Unsupported file extension '{suffix}'. Allowed: {', '.join(sorted(allowed))}"
        )
    return suffix


async def save_upload(
    upload: UploadFile,
    destination_dir: Path,
    allowed_extensions: set[str],
    max_size_mb: int,
) -> tuple[str, Path, int]:
    """Validates and streams an UploadFile to disk under a generated UUID filename.

    Returns (generated_id, saved_path, size_bytes).
    """
    if not upload.filename:
        raise FileValidationError("No filename provided.")

    suffix = _safe_suffix(upload.filename, allowed_extensions)
    generated_id = uuid.uuid4().hex
    safe_name = f"{generated_id}{suffix}"
    destination_path = destination_dir / safe_name

    max_bytes = max_size_mb * 1024 * 1024
    size = 0

    with open(destination_path, "wb") as out_file:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out_file.close()
                destination_path.unlink(missing_ok=True)
                raise FileValidationError(f"File exceeds maximum size of {max_size_mb} MB.")
            out_file.write(chunk)

    if size == 0:
        destination_path.unlink(missing_ok=True)
        raise FileValidationError("Uploaded file is empty.")

    return generated_id, destination_path, size
