"""Terrain line of sight between two points on the planning DTM (FR-05; proje.md §6 viewshed; D015).

The DTM holds elevations at cell centres. The ground under the sight line is interpolated
bilinearly at ≤ 1 m steps; observer heights follow the spec viewshed (EV 2 m, antenna 3 m).
The result is the signed clearance: the smallest height of the sight line above the ground
(positive = visible). There is no curvature term: at 100 m it is ≈ 1.5 mm, far below the DTM
error. Relief smaller than the 4 m grid is not seen, so the result is DERIVED, not an observation.
"""
from __future__ import annotations

import math

import numpy as np


def _ground(z: np.ndarray, origin_xy: tuple[float, float], resolution_m: float, xs, ys) -> np.ndarray:
    fx = (np.asarray(xs) - origin_xy[0]) / resolution_m - 0.5
    fy = (np.asarray(ys) - origin_xy[1]) / resolution_m - 0.5
    h, w = z.shape
    fx = np.clip(fx, 0.0, w - 1.0)
    fy = np.clip(fy, 0.0, h - 1.0)
    x0 = np.minimum(np.floor(fx).astype(int), w - 2) if w > 1 else np.zeros_like(fx, dtype=int)
    y0 = np.minimum(np.floor(fy).astype(int), h - 2) if h > 1 else np.zeros_like(fy, dtype=int)
    tx, ty = fx - x0, fy - y0
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    top = z[y0, x0] * (1 - tx) + z[y0, x1] * tx
    bottom = z[y1, x0] * (1 - tx) + z[y1, x1] * tx
    return top * (1 - ty) + bottom * ty


def sight_clearance(z: np.ndarray, origin_xy: tuple[float, float], resolution_m: float,
                    a_xy: tuple[float, float], b_xy: tuple[float, float], height_a_m: float,
                    height_b_m: float, step_m: float = 1.0) -> float:
    """Smallest height of the a→b sight line above the ground; NaN if the profile has no terrain.

    Raises ValueError when an endpoint is outside the grid or has no terrain.
    """
    z = np.asarray(z, dtype=float)
    h, w = z.shape
    for x, y in (a_xy, b_xy):
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("line-of-sight endpoints must be finite")
        if not (origin_xy[0] <= x < origin_xy[0] + w * resolution_m
                and origin_xy[1] <= y < origin_xy[1] + h * resolution_m):
            raise ValueError(f"line-of-sight endpoint {(x, y)} is outside the grid")
    length = math.hypot(b_xy[0] - a_xy[0], b_xy[1] - a_xy[1])
    n = max(1, int(math.ceil(length / step_m)))
    t = np.linspace(0.0, 1.0, n + 1)
    xs = a_xy[0] + t * (b_xy[0] - a_xy[0])
    ys = a_xy[1] + t * (b_xy[1] - a_xy[1])
    ground = _ground(z, origin_xy, resolution_m, xs, ys)
    if not (math.isfinite(ground[0]) and math.isfinite(ground[-1])):
        raise ValueError("a line-of-sight endpoint has no terrain")
    if not np.isfinite(ground).all():
        return math.nan
    line = (ground[0] + height_a_m) + t * ((ground[-1] + height_b_m) - (ground[0] + height_a_m))
    return float(np.min(line - ground))
