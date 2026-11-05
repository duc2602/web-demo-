"""Synthetic image degradations shared by inference and dataset generation."""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def add_gaussian_noise(
    image: np.ndarray,
    sigma: float,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Synthesize Gaussian noise with sigma on the 0-255 pixel scale."""
    generator = rng if rng is not None else np.random.default_rng()
    noise = generator.normal(0.0, sigma, image.shape)
    noisy = image.astype(np.float32) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def degrade_image(
    image: np.ndarray,
    mode: str,
    noise_sigma: float = 25.0,
    strength: int = 25,
    seed: int | None = None,
) -> np.ndarray:
    generator = np.random.default_rng(seed)
    severity = min(1.0, max(0.0, strength / 100))
    if mode == "synthetic_noise":
        return add_gaussian_noise(image, noise_sigma, generator)
    if mode == "blur":
        radius = 0.5 + 8 * severity**1.2
        return np.asarray(Image.fromarray(image).filter(ImageFilter.GaussianBlur(radius)))

    height, width = image.shape[:2]
    border = np.concatenate((image[0], image[-1], image[:, 0], image[:, -1]), axis=0)
    background = tuple(np.percentile(border, 90, axis=0).astype(np.uint8).tolist())
    degraded = Image.fromarray(image.copy())
    draw = ImageDraw.Draw(degraded)

    if mode == "broken":
        grayscale = image.mean(axis=2)
        background_luma = float(np.mean(background))
        ink_mask = grayscale < background_luma - 35 if background_luma >= 128 else grayscale > background_luma + 35
        ink_y, ink_x = np.where(ink_mask)
        sample_count = len(ink_x)
        if sample_count == 0:
            ink_x = generator.integers(0, width, size=1)
            ink_y = generator.integers(0, height, size=1)
            sample_count = 1
        gap_length = 2 + round(8 * severity)
        line_width = 1 + int(severity)
        broken_fraction = 0.02 + 0.48 * severity**1.5
        gap_count = min(600, max(1, round(sample_count * broken_fraction / (gap_length * line_width))))
        for _ in range(gap_count):
            index = int(generator.integers(sample_count))
            x, y = int(ink_x[index]), int(ink_y[index])
            angle = float(generator.uniform(0, np.pi))
            dx = np.cos(angle) * gap_length / 2
            dy = np.sin(angle) * gap_length / 2
            draw.line((x - dx, y - dy, x + dx, y + dy), fill=background, width=line_width)
    elif mode == "missing":
        grayscale = image.mean(axis=2)
        background_luma = float(np.mean(background))
        ink_mask = grayscale < background_luma - 35 if background_luma >= 128 else grayscale > background_luma + 35
        ink_y, ink_x = np.where(ink_mask)
        target_missing = int(height * width * (0.02 + 0.35 * severity**1.35))
        missing_mask = np.zeros((height, width), dtype=bool)
        missing_pixels = 0
        attempts = 0
        while missing_pixels < target_missing and attempts < 200:
            attempts += 1
            patch_width = max(2, round(width * generator.uniform(0.06 + 0.02 * severity, 0.12 + 0.08 * severity)))
            patch_height = max(2, round(height * generator.uniform(0.04 + 0.02 * severity, 0.08 + 0.08 * severity)))
            if len(ink_x):
                index = int(generator.integers(len(ink_x)))
                left = int(np.clip(ink_x[index] - patch_width // 2, 0, max(0, width - patch_width)))
                top = int(np.clip(ink_y[index] - patch_height // 2, 0, max(0, height - patch_height)))
            else:
                left = int(generator.integers(max(1, width - patch_width + 1)))
                top = int(generator.integers(max(1, height - patch_height + 1)))
            right = min(width, left + patch_width + 1)
            bottom = min(height, top + patch_height + 1)
            patch_mask = missing_mask[top:bottom, left:right]
            new_pixels = patch_mask.size - int(np.count_nonzero(patch_mask))
            if new_pixels:
                draw.rectangle((left, top, left + patch_width, top + patch_height), fill=background)
                patch_mask[:] = True
                missing_pixels += new_pixels
    elif mode == "occlusion":
        block_count = min(8, max(1, round(1 + 4 * severity)))
        for _ in range(block_count):
            block_width = max(2, round(width * generator.uniform(0.07 + 0.08 * severity, 0.12 + 0.16 * severity)))
            block_height = max(2, round(height * generator.uniform(0.05 + 0.06 * severity, 0.09 + 0.13 * severity)))
            left = int(generator.integers(max(1, width - block_width + 1)))
            top = int(generator.integers(max(1, height - block_height + 1)))
            color = tuple(int(channel) for channel in generator.integers(24, 96, size=3))
            draw.rectangle((left, top, left + block_width, top + block_height), fill=color)
    else:
        raise ValueError(f"Unsupported degradation mode: {mode}")

    return np.asarray(degraded)