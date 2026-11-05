"""Load Restormer checkpoints and infer their network dimensions from weights."""

from pathlib import Path
from collections.abc import Mapping
from typing import Any
import os

import numpy as np
import torch

from app.utils.logger import get_logger

logger = get_logger(__name__)

# --- Model configuration -----------------------------------------------------
# Placeholder init_params based on the commonly published Restormer defaults.
# Confirm these match the config you actually trained with before relying on
# real output quality - a mismatch here will load with wrong-shaped weights
# and either error out or silently degrade quality.
MODEL_CONFIG: dict[str, Any] = {
    "output_scale": 1,
}


def _extract_state_dict(checkpoint: Any) -> dict[str, torch.Tensor]:
    if isinstance(checkpoint, Mapping):
        for key in ("params", "params_ema", "state_dict", "model_state_dict", "model", "net_g"):
            candidate = checkpoint.get(key)
            if isinstance(candidate, Mapping) and any(isinstance(value, torch.Tensor) for value in candidate.values()):
                checkpoint = candidate
                break

    if not isinstance(checkpoint, Mapping):
        raise ModelLoadError("Unsupported checkpoint: expected a state dictionary of model weights.")

    state_dict = {str(key): value for key, value in checkpoint.items() if isinstance(value, torch.Tensor)}
    for prefix in ("module.", "net_g.", "model."):
        if state_dict and all(key.startswith(prefix) for key in state_dict):
            state_dict = {key[len(prefix):]: value for key, value in state_dict.items()}

    if "patch_embed.proj.weight" not in state_dict:
        raise ModelLoadError(
            "Unsupported architecture. Automatic configuration is available for Restormer checkpoints only."
        )
    return state_dict


def _block_count(state_dict: dict[str, torch.Tensor], prefix: str) -> int:
    indices = {
        int(key[len(prefix):].split(".", 1)[0])
        for key in state_dict
        if key.startswith(prefix) and key[len(prefix):].split(".", 1)[0].isdigit()
    }
    if not indices or indices != set(range(max(indices) + 1)):
        raise ModelLoadError(f"Could not infer a complete Restormer block sequence: {prefix.rstrip('.')}.")
    return len(indices)


def _infer_restormer_params(state_dict: dict[str, torch.Tensor]) -> dict[str, Any]:
    patch_weight = state_dict["patch_embed.proj.weight"]
    output_weight = state_dict.get("output.weight")
    if patch_weight.ndim != 4 or output_weight is None or output_weight.ndim != 4:
        raise ModelLoadError("Checkpoint does not have the expected Restormer input/output layers.")

    dim = int(patch_weight.shape[0])
    stage_prefixes = ["encoder_level1.", "encoder_level2.", "encoder_level3.", "latent."]
    num_blocks = [_block_count(state_dict, prefix) for prefix in stage_prefixes]
    num_refinement_blocks = _block_count(state_dict, "refinement.")

    heads = []
    for prefix in stage_prefixes:
        temperature = state_dict.get(f"{prefix}0.attn.temperature")
        if temperature is None or temperature.ndim < 1:
            raise ModelLoadError("Could not infer Restormer attention heads from checkpoint weights.")
        heads.append(int(temperature.shape[0]))

    expansion_bounds = []
    for stage_index, prefix in enumerate(stage_prefixes):
        ffn_weight = state_dict.get(f"{prefix}0.ffn.project_in.weight")
        if ffn_weight is None or ffn_weight.shape[0] % 2:
            raise ModelLoadError("Could not infer Restormer FFN dimensions from checkpoint weights.")
        hidden_features = int(ffn_weight.shape[0]) // 2
        stage_dim = dim * (2 ** stage_index)
        expansion_bounds.append((hidden_features / stage_dim, (hidden_features + 1) / stage_dim))

    expansion_min = max(lower for lower, _ in expansion_bounds)
    expansion_max = min(upper for _, upper in expansion_bounds)
    if expansion_min >= expansion_max:
        raise ModelLoadError("Checkpoint has inconsistent Restormer FFN dimensions across stages.")
    ffn_expansion_factor = (expansion_min + expansion_max) / 2

    return {
        "inp_channels": int(patch_weight.shape[1]),
        "out_channels": int(output_weight.shape[0]),
        "dim": dim,
        "num_blocks": num_blocks,
        "num_refinement_blocks": num_refinement_blocks,
        "heads": heads,
        "ffn_expansion_factor": ffn_expansion_factor,
        "bias": "encoder_level1.0.attn.qkv.bias" in state_dict,
        "LayerNorm_type": "WithBias" if "encoder_level1.0.norm1.body.bias" in state_dict else "BiasFree",
        "dual_pixel_task": "skip_conv.weight" in state_dict,
    }


def resolve_device(requested: str = "auto") -> torch.device:
    if requested == "cpu":
        return torch.device("cpu")
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available on this machine.")
        return torch.device("cuda")
    # auto
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class ModelLoadError(Exception):
    pass


class ModelLoader:
    """Loads a Restormer checkpoint and runs inference on preprocessed tiles."""

    def __init__(self) -> None:
        torch.set_num_threads(min(4, os.cpu_count() or 1))
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass

    def load(self, model_path: Path, device: str = "auto") -> tuple[torch.nn.Module, torch.device]:
        try:
            from app.inference.architectures.restormer_arch import Restormer
        except ImportError as e:  # pragma: no cover
            raise ModelLoadError(
                "Restormer architecture module could not be imported. See "
                "app/inference/architectures/restormer_arch.py for setup instructions."
            ) from e

        try:
            resolved_device = resolve_device(device)
        except RuntimeError as e:
            raise ModelLoadError(
                "CUDA was selected but no GPU is available on this machine. "
                "Set Device to Auto or CPU in Settings."
            ) from e

        try:
            checkpoint = torch.load(model_path, map_location=resolved_device, weights_only=True)
        except Exception as e:
            raise ModelLoadError(f"Failed to read checkpoint file: {e}") from e

        state_dict = _extract_state_dict(checkpoint)
        init_params = _infer_restormer_params(state_dict)

        try:
            model = Restormer(**init_params)
        except NotImplementedError as e:
            raise ModelLoadError(str(e)) from e
        except Exception as e:
            raise ModelLoadError(f"Failed to instantiate Restormer from checkpoint dimensions: {e}") from e

        try:
            model.load_state_dict(state_dict, strict=True)
        except Exception as e:
            raise ModelLoadError(
                "Failed to load model. Please verify that the model format and "
                f"architecture are supported. Detail: {e}"
            ) from e

        model.to(resolved_device)
        model.eval()
        logger.info(
            "Loaded Restormer checkpoint %s (dim=%s, blocks=%s, heads=%s) on device %s",
            model_path.name,
            init_params["dim"],
            init_params["num_blocks"],
            init_params["heads"],
            resolved_device,
        )
        return model, resolved_device

    @torch.no_grad()
    def predict_batch(
        self,
        model: torch.nn.Module,
        device: torch.device,
        tiles: list[np.ndarray],
    ) -> list[np.ndarray]:
        """Run a batch of HWC uint8 tiles through the model, return HWC uint8 outputs."""
        batch = np.stack(tiles, axis=0).astype(np.float32) / 255.0  # NHWC, [0,1]
        tensor = torch.from_numpy(batch).permute(0, 3, 1, 2).to(device)  # NCHW

        output = model(tensor)

        output = output.clamp(0.0, 1.0)
        output_np = (output.permute(0, 2, 3, 1).cpu().numpy() * 255.0).round().astype(np.uint8)
        return [output_np[i] for i in range(output_np.shape[0])]
