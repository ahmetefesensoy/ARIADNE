"""Test-only builders for planning grids; not part of the redline_core API."""
from __future__ import annotations

import numpy as np

from redline_core.cost_human import DETECTED
from redline_core.grid import Grid

# Hand-derived from proje.md §7.2: v(0) = sqrt(3.721/9.80665)·6·exp(-3.5·0.05)/3.6 m/s.
V_FLAT = 0.8618202859411123


def terrain_grid(
    z,
    resolution_m: float = 4.0,
    *,
    state=DETECTED,
    slope_deg=0.0,
    sigma_deg=0.0,
    relief_m=0.0,
    wall_slope_deg=None,
    origin_xy=(0.0, 0.0),
    extra=None,
) -> Grid:
    z = np.asarray(z, dtype=float)
    shape = z.shape

    def full(value, dtype=float):
        return np.broadcast_to(np.asarray(value, dtype=dtype), shape).copy()

    slope = full(slope_deg)
    layers = {
        "z_m": z,
        "slope_deg": slope,
        "slope_sigma_deg": full(sigma_deg),
        "state": full(state, np.uint8),
        "relief_m": full(relief_m),
        "wall_slope_deg": slope.copy() if wall_slope_deg is None else full(wall_slope_deg),
    }
    layers.update(extra or {})
    return Grid(origin_xy, resolution_m, width=shape[1], height=shape[0], layers=layers)
