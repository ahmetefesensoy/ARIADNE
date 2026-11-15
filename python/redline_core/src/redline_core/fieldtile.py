"""Compressed grid tiles for Unreal, web and Open MCT (FieldTile.msg, proje.md §5.1).

Only `FieldTile` PNGs and `RedLine` polygons leave ROS; float grids stay inside.

Contract (docs/DECISIONS.md D009):

- The PNG is a north-up image: PNG row 0 is the **north** edge of the grid and
  column 0 the west edge. `origin` keeps the meaning it has in every grid
  message: the south-west corner of grid cell (0, 0) in the `map` frame.
- ``value = code * scale + offset``. A sample equal to ``nodata_byte``
  (zero-extended in a 16-bit PNG) is missing. Only an end of the code range may
  be nodata: 0 for 8 or 16 bit, or 255 for 8 bit.
- NaN becomes nodata. ±inf and values outside ``[lo, hi]`` are clamped to that
  end of the range, so the tile cannot show an out-of-range cell as safe.
- `scale` and `offset` are rounded to float32 *before* quantising, exactly as
  the message stores them, so a consumer decodes with the encoder's numbers.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True, eq=False)
class Tile:
    png: bytes
    width: int
    height: int
    scale: float
    offset: float
    nodata_byte: int
    bit_depth: int


def _code_range(bit_depth: int, nodata_byte: int) -> tuple[int, int]:
    if bit_depth not in (8, 16):
        raise ValueError("bit_depth must be 8 or 16")
    max_code = (1 << bit_depth) - 1
    if nodata_byte == 0:
        return 1, max_code
    if bit_depth == 8 and nodata_byte == 255:
        return 0, 254
    raise ValueError("nodata_byte must be 0, or 255 for an 8-bit tile (an end of the code range)")


def _f32(value: float) -> float:
    return float(np.float32(value))


def encode_tile(values, lo: float, hi: float, *, bit_depth: int = 16, nodata_byte: int = 0,
                step: float | None = None, compress_level: int = 6) -> Tile:
    """Quantise a grid-order array (row 0 = south) into a north-up grey PNG.

    Without `step` the whole code range spans ``[lo, hi]``. A coarser explicit
    `step` (value units per code) leaves high codes unused and compresses
    better; ``(hi - lo) / step`` must fit in the code range.
    """
    a = np.asarray(values, dtype=float)
    if a.ndim != 2 or a.size == 0:
        raise ValueError("a tile needs a non-empty 2-D array")
    if not (math.isfinite(lo) and math.isfinite(hi) and hi > lo):
        raise ValueError("tile range needs finite lo < hi")
    first, last = _code_range(bit_depth, nodata_byte)
    if step is None:
        scale = _f32((hi - lo) / (last - first))
    else:
        if not (math.isfinite(step) and step > 0):
            raise ValueError("step must be positive and finite")
        scale = _f32(step)
        if (hi - lo) / scale > last - first:
            raise ValueError(f"range [{lo}, {hi}] needs more than {last - first} steps of {step}")
    offset = _f32(lo - first * scale)
    if not scale > 0:
        raise ValueError("tile range is too narrow for float32 scale")

    missing = np.isnan(a)
    clamped = np.clip(np.where(missing, lo, a), lo, hi)  # ±inf clip to the range ends
    codes = np.clip(np.rint((clamped - offset) / scale), first, last)
    codes[missing] = nodata_byte
    dtype = np.uint8 if bit_depth == 8 else np.uint16
    image = np.ascontiguousarray(codes[::-1].astype(dtype))  # grid row 0 (south) -> PNG bottom row
    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="PNG", compress_level=compress_level)
    return Tile(buffer.getvalue(), a.shape[1], a.shape[0], scale, offset, int(nodata_byte), bit_depth)


def decode_tile(png: bytes, scale: float, offset: float, nodata_byte: int) -> np.ndarray:
    """Inverse of :func:`encode_tile`: grid-order float array, NaN where missing."""
    with Image.open(io.BytesIO(png)) as image:
        if image.mode not in ("L", "I;16", "I;16B", "I"):
            raise ValueError(f"FieldTile PNG must be greyscale, got mode {image.mode}")
        codes = np.asarray(image).astype(np.int64)
    values = codes * float(scale) + float(offset)
    values = np.where(codes == int(nodata_byte), np.nan, values)
    return np.ascontiguousarray(values[::-1])
