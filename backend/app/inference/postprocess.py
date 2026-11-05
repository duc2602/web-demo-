"""Image I/O helpers used before/after the tiling + model pipeline."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def load_image_as_array(path: Path) -> np.ndarray:
    """Load any common image format, drop alpha, return HWC uint8 RGB array."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        return np.array(img)


def save_array_as_image(array: np.ndarray, path: Path) -> None:
    Image.fromarray(array, mode="RGB").save(path)


def get_image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        return img.width, img.height
