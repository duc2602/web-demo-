"""
Full inference pipeline: load model once, tile the image, run the model over
tiles (optionally batched), reconstruct with feather blending, crop to the
original resolution, save the output.

Also supports a "full_image" mode that skips tiling entirely and runs the
model on the whole image in one shot (only safe when there's enough VRAM/RAM).
"""

from pathlib import Path
from typing import Callable, Optional
import uuid

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from app.inference.degradations import add_gaussian_noise, degrade_image
from app.inference import tiler
from app.inference.model_loader import MODEL_CONFIG, ModelLoader, ModelLoadError
from app.inference.preprocessing import preprocess_phone_photos
from app.inference.postprocess import get_image_dimensions, load_image_as_array, save_array_as_image
from app.utils.logger import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[int, int], None]  # (processed_tiles, total_tiles)


def _compute_metrics(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Generic PSNR/SSIM between two same-shape images. Returns (psnr, ssim)."""
    if a.shape != b.shape:
        return 0.0, 0.0

    psnr = float(peak_signal_noise_ratio(a, b, data_range=255))
    if not np.isfinite(psnr):
        psnr = 100.0  # identical images -> cap instead of returning inf (breaks JSON)
    ssim = float(structural_similarity(a, b, channel_axis=2, data_range=255))
    return round(psnr, 2), round(ssim, 4)


class InferencePipeline:
    def __init__(self) -> None:
        self.loader = ModelLoader()

    def run(
        self,
        model_path: Path,
        input_path: Path,
        output_path: Path,
        tile_size: int = 128,
        tile_overlap: int = 16,
        batch_size: int = 1,
        device: str = "auto",
        processing_mode: str = "tile",
        degradation_mode: str = "direct",
        noise_sigma: float = 25.0,
        degradation_strength: int = 25,
        degraded_output_path: Optional[Path] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> dict:
        """Returns a result dict with input/output dimensions, tile info, and metrics.

        degradation_mode:
          - "direct": the uploaded image is fed to the model as-is (normal usage).
            Metrics are computed vs that same input (measures how much the model
            changed the image - not an accuracy score, since there's no ground truth).
          - Synthetic modes treat the preprocessed image as CLEAN ground truth. The
            selected degradation is applied to a copy, that degraded image is fed
            to the model, and restoration metrics are also computed vs the clean
            reference.
        """

        orig_w, orig_h = get_image_dimensions(input_path)
        source_images = preprocess_phone_photos(load_image_as_array(input_path))
        model_input_images = [
            degrade_image(
                image,
                degradation_mode,
                noise_sigma=noise_sigma,
                strength=degradation_strength,
            )
            if degradation_mode != "direct"
            else image
            for image in source_images
        ]

        model, resolved_device = self.loader.load(model_path, device=device)
        output_scale = MODEL_CONFIG["output_scale"]
        total_units = sum(
            1
            if processing_mode == "full_image"
            else tiler.build_tile_plan(image.shape[1], image.shape[0], tile_size, tile_overlap).total
            for image in model_input_images
        )
        completed_units = 0
        page_results = []

        for page_index, (source_image, model_input_image) in enumerate(
            zip(source_images, model_input_images)
        ):
            page_output_path = (
                output_path
                if page_index == 0
                else output_path.with_name(f"{uuid.uuid4().hex}.png")
            )
            page_degraded_path = None
            if degradation_mode != "direct" and degraded_output_path is not None:
                page_degraded_path = (
                    degraded_output_path
                    if page_index == 0
                    else degraded_output_path.with_name(f"{uuid.uuid4().hex}.png")
                )
                save_array_as_image(model_input_image, page_degraded_path)

            def page_progress(processed: int, total: int) -> None:
                if on_progress:
                    on_progress(completed_units + processed, total_units)

            if processing_mode == "full_image":
                result_array = self._run_full_image(
                    model, resolved_device, model_input_image, page_progress
                )
                tile_info = {"tile_size": 0, "overlap": 0, "columns": 1, "rows": 1, "total": 1}
            else:
                result_array, tile_info = self._run_tiled(
                    model, resolved_device, model_input_image, tile_size, tile_overlap,
                    batch_size, output_scale, page_progress
                )
            save_array_as_image(result_array, page_output_path)

            psnr_in, ssim_in = _compute_metrics(model_input_image, result_array)
            metrics = {
                "psnr_vs_input": psnr_in,
                "ssim_vs_input": ssim_in,
                "psnr_vs_ground_truth": None,
                "ssim_vs_ground_truth": None,
            }
            if degradation_mode != "direct":
                psnr_gt, ssim_gt = _compute_metrics(source_image, result_array)
                metrics["psnr_vs_ground_truth"] = psnr_gt
                metrics["ssim_vs_ground_truth"] = ssim_gt

            page_results.append(
                {
                    "output_id": page_output_path.stem,
                    "degraded_id": page_degraded_path.stem if page_degraded_path else None,
                    "input": {"width": source_image.shape[1], "height": source_image.shape[0]},
                    "output": {"width": result_array.shape[1], "height": result_array.shape[0]},
                    "tiles": tile_info,
                    "metrics": metrics,
                }
            )
            completed_units += tile_info["total"]
            if on_progress:
                on_progress(completed_units, total_units)

        first_page = page_results[0]

        return {
            "input": {"width": orig_w, "height": orig_h},
            "output": first_page["output"],
            "tiles": first_page["tiles"],
            "metrics": first_page["metrics"],
            "pages": page_results,
        }

    def _run_tiled(
        self,
        model,
        device,
        image: np.ndarray,
        tile_size: int,
        overlap: int,
        batch_size: int,
        output_scale: int,
        on_progress: Optional[ProgressCallback],
    ) -> tuple[np.ndarray, dict]:
        h, w = image.shape[0], image.shape[1]
        grid = tiler.build_tile_plan(w, h, tile_size, overlap)
        padded = tiler.pad_image(image, grid)
        input_tiles = tiler.extract_tiles(padded, grid)

        output_tiles: list[np.ndarray] = []
        total = len(input_tiles)
        processed = 0

        for start in range(0, total, batch_size):
            batch = input_tiles[start : start + batch_size]
            try:
                batch_out = self.loader.predict_batch(model, device, batch)
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    raise ModelLoadError(
                        "GPU out of memory. Try using a smaller batch size or CPU mode."
                    ) from e
                raise
            output_tiles.extend(batch_out)
            processed += len(batch)
            if on_progress:
                on_progress(processed, total)

        result = tiler.reconstruct_from_tiles(output_tiles, grid, output_scale=output_scale)

        tile_info = {
            "tile_size": tile_size,
            "overlap": overlap,
            "columns": grid.columns,
            "rows": grid.rows,
            "total": grid.total,
        }
        return result, tile_info

    def _run_full_image(
        self,
        model,
        device,
        image: np.ndarray,
        on_progress: Optional[ProgressCallback],
    ) -> np.ndarray:
        if on_progress:
            on_progress(0, 1)

        # Restormer downsamples 3 times, so height/width must be multiples of 8.
        # Reflect-pad up to the next multiple of 8, then crop back afterwards.
        orig_h, orig_w = image.shape[:2]
        pad_h = (-orig_h) % 8
        pad_w = (-orig_w) % 8
        if pad_h or pad_w:
            image = np.pad(image, ((0, pad_h), (0, pad_w), (0, 0)), mode="reflect")

        try:
            output = self.loader.predict_batch(model, device, [image])[0]
            output = output[:orig_h, :orig_w, :]
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                raise ModelLoadError(
                    "GPU out of memory. Try tile mode or CPU mode for large images."
                ) from e
            raise
        if on_progress:
            on_progress(1, 1)
        return output