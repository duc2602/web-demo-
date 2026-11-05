"""
Image tiling and reconstruction utilities.

Design goals (see project spec):
- Never resize the whole input image; split into TILE_SIZE x TILE_SIZE tiles instead.
- Handle images whose dimensions are NOT divisible by TILE_SIZE, via reflect padding,
  without losing any data.
- Support overlapping tiles + feather (linear) blending on the overlap region to avoid
  visible seams, which matters for transformer-based restoration models like Restormer
  that were not trained to be seam-consistent across independently processed tiles.
- Reconstruct an output that exactly matches the original input resolution.
"""

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class TileGridInfo:
    tile_size: int
    overlap: int
    columns: int
    rows: int
    total: int
    padded_width: int
    padded_height: int
    original_width: int
    original_height: int


@dataclass
class TileCoord:
    row: int
    col: int
    x: int  # top-left x in padded image
    y: int  # top-left y in padded image


def _compute_grid(width: int, height: int, tile_size: int, overlap: int) -> TileGridInfo:
    """Compute how many tiles are needed and the padded canvas size.

    The effective stride between tile origins is (tile_size - overlap); this ensures
    consecutive tiles overlap by `overlap` pixels on each shared edge, which gives the
    blending step room to feather the seam.
    """
    if tile_size <= overlap:
        raise ValueError("tile_size must be greater than overlap")

    stride = tile_size - overlap

    def tiles_needed(dim: int) -> int:
        if dim <= tile_size:
            return 1
        # number of strides needed to cover (dim - tile_size), then +1 for the first tile
        return 1 + math.ceil((dim - tile_size) / stride)

    columns = tiles_needed(width)
    rows = tiles_needed(height)

    padded_width = max(width, tile_size + (columns - 1) * stride)
    padded_height = max(height, tile_size + (rows - 1) * stride)

    return TileGridInfo(
        tile_size=tile_size,
        overlap=overlap,
        columns=columns,
        rows=rows,
        total=columns * rows,
        padded_width=padded_width,
        padded_height=padded_height,
        original_width=width,
        original_height=height,
    )


def pad_image(image: np.ndarray, grid: TileGridInfo) -> np.ndarray:
    """Reflect-pad an HWC uint8/float image to the padded canvas size.

    Reflect padding is used (instead of zero padding) because it keeps pixel
    statistics closer to the real image content at the borders, which restoration
    models tend to handle better than hard black edges.
    """
    pad_bottom = grid.padded_height - image.shape[0]
    pad_right = grid.padded_width - image.shape[1]
    if pad_bottom == 0 and pad_right == 0:
        return image
    return np.pad(
        image,
        ((0, pad_bottom), (0, pad_right), (0, 0)),
        mode="reflect",
    )


def get_tile_coords(grid: TileGridInfo) -> list[TileCoord]:
    stride = grid.tile_size - grid.overlap
    coords = []
    for row in range(grid.rows):
        y = min(row * stride, grid.padded_height - grid.tile_size)
        for col in range(grid.columns):
            x = min(col * stride, grid.padded_width - grid.tile_size)
            coords.append(TileCoord(row=row, col=col, x=x, y=y))
    return coords


def extract_tiles(padded_image: np.ndarray, grid: TileGridInfo) -> list[np.ndarray]:
    coords = get_tile_coords(grid)
    ts = grid.tile_size
    return [padded_image[c.y : c.y + ts, c.x : c.x + ts, :] for c in coords]


def _feather_weight_map(tile_size: int, overlap: int) -> np.ndarray:
    """1D ramp that is 1.0 in the tile center and linearly fades to a small epsilon
    over the overlap region at each edge. Combined as an outer product for 2D weight.
    """
    if overlap <= 0:
        return np.ones((tile_size, tile_size, 1), dtype=np.float32)

    ramp = np.ones(tile_size, dtype=np.float32)
    fade = np.linspace(0.0, 1.0, overlap, endpoint=False, dtype=np.float32)
    fade = np.clip(fade, 1e-3, 1.0)
    ramp[:overlap] = fade
    ramp[-overlap:] = fade[::-1]

    weight_2d = np.outer(ramp, ramp)
    return weight_2d[:, :, None]


def reconstruct_from_tiles(
    tiles: list[np.ndarray],
    grid: TileGridInfo,
    output_scale: int = 1,
) -> np.ndarray:
    """Blend output tiles back into a full padded canvas using feather weights on the
    overlap region, then crop to the original (scaled) resolution.
    """
    ts = grid.tile_size * output_scale
    overlap = grid.overlap * output_scale
    coords = get_tile_coords(grid)

    canvas_h = grid.padded_height * output_scale
    canvas_w = grid.padded_width * output_scale

    channels = tiles[0].shape[2]
    accum = np.zeros((canvas_h, canvas_w, channels), dtype=np.float32)
    weight_accum = np.zeros((canvas_h, canvas_w, 1), dtype=np.float32)

    weight_map = _feather_weight_map(ts, overlap)

    for tile, coord in zip(tiles, coords):
        y = coord.y * output_scale
        x = coord.x * output_scale
        accum[y : y + ts, x : x + ts, :] += tile.astype(np.float32) * weight_map
        weight_accum[y : y + ts, x : x + ts, :] += weight_map

    weight_accum = np.clip(weight_accum, 1e-6, None)
    blended = accum / weight_accum

    out_w = grid.original_width * output_scale
    out_h = grid.original_height * output_scale
    cropped = blended[:out_h, :out_w, :]

    return np.clip(cropped, 0, 255).astype(np.uint8)


def build_tile_plan(width: int, height: int, tile_size: int, overlap: int) -> TileGridInfo:
    """Public entry point: compute the tiling grid for a given image size."""
    return _compute_grid(width, height, tile_size, overlap)
