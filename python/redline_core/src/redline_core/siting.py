"""Habitat site selection on the planning grid (D010).

A habitat cell must sit on a safe pad and serve the EVA area:

- **Pad** (MSL landing-site engineering limits, MSL Engineering User Guide v2: slopes ≤ 15°
  over 2–5 m and ≤ 5° over 200–500 m): every cell of a ``pad_cells`` × ``pad_cells`` square
  is walkable and satisfies ``|μ| + z·σ ≤ local_max_deg``, and the least-squares plane over
  a ``regional_window_m`` square around it has slope ≤ ``regional_max_deg``.
- **Reach**: among pad candidates in the largest walkable component and within
  ``search_radius_m`` of the requested point, the habitat maximises the walkable area whose
  risk-adjusted return time is ≤ ``reach_budget_s``. Ties go to the candidate nearest the
  request. The result is SCENARIO (it is a chosen site, not a mapped one).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from .cost_human import PreparedTerrain
from .walkback import walkable_components, walkback


@dataclass(frozen=True)
class SitingRules:
    pad_cells: int = 5
    local_max_deg: float = 15.0
    regional_window_m: float = 200.0
    regional_max_deg: float = 5.0
    z: float = 1.645
    search_radius_m: float = 600.0
    lattice_m: float = 40.0
    reach_budget_s: float = 3600.0
    z_eps: float = 1.645
    sigma_theta: float = 0.2


def regional_slope_deg(z: np.ndarray, resolution_m: float, window_m: float) -> np.ndarray:
    """Slope of the least-squares plane over a square window centred on each cell."""
    n = max(3, int(round(window_m / resolution_m)) | 1)
    valid = np.isfinite(z)
    zz = np.where(valid, z, 0.0)
    h, w = z.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(float) * resolution_m

    def box(a):
        return ndimage.uniform_filter(a, n, mode="nearest")

    count = box(valid.astype(float))
    with np.errstate(invalid="ignore", divide="ignore"):
        mx, my, mz = box(xx * valid) / count, box(yy * valid) / count, box(zz) / count
        sxx = box(xx * xx * valid) / count - mx * mx
        syy = box(yy * yy * valid) / count - my * my
        sxy = box(xx * yy * valid) / count - mx * my
        sxz = box(xx * zz) / count - mx * mz
        syz = box(yy * zz) / count - my * mz
        det = sxx * syy - sxy * sxy
        gx = (syy * sxz - sxy * syz) / det
        gy = (sxx * syz - sxy * sxz) / det
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    slope[count < 0.5] = np.nan
    return slope


def pad_mask(terrain: PreparedTerrain, slope_deg: np.ndarray, sigma_deg: np.ndarray,
             rules: SitingRules) -> np.ndarray:
    """Cells that can centre a habitat pad under the local and regional slope limits."""
    shape = (terrain.height, terrain.width)
    banned = terrain.banned_mask
    sigma = np.where(np.isfinite(sigma_deg), sigma_deg, np.inf)  # unknown σ never passes
    local_ok = ~banned & np.isfinite(slope_deg) & (np.abs(slope_deg) + rules.z * sigma <= rules.local_max_deg)
    k = rules.pad_cells
    if k < 1 or k % 2 == 0:
        raise ValueError("pad_cells must be a positive odd integer")
    pad_ok = ndimage.minimum_filter(local_ok.astype(np.uint8), size=k, mode="constant", cval=0).astype(bool)
    regional = regional_slope_deg(terrain.z.reshape(shape), terrain.resolution_m, rules.regional_window_m)
    return pad_ok & np.isfinite(regional) & (regional <= rules.regional_max_deg)


@dataclass(frozen=True)
class SitingResult:
    cell: tuple[int, int]
    reach_cells: int
    candidates_evaluated: int
    pad_cells_total: int
    ranking: list[dict]


def select_habitat(terrain: PreparedTerrain, slope_deg: np.ndarray, sigma_deg: np.ndarray,
                   requested_cell: tuple[int, int], rules: SitingRules = SitingRules()) -> SitingResult:
    pads = pad_mask(terrain, slope_deg, sigma_deg, rules)
    labels = walkable_components(terrain)
    sizes = np.bincount(labels[labels >= 0])
    if sizes.size == 0:
        raise ValueError("no walkable cell")
    largest = int(np.argmax(sizes))
    r = terrain.resolution_m
    ry, rx = requested_cell
    yy, xx = np.mgrid[0:terrain.height, 0:terrain.width]
    near = np.hypot(yy - ry, xx - rx) * r <= rules.search_radius_m
    step = max(1, int(round(rules.lattice_m / r)))
    lattice = ((yy - ry) % step == 0) & ((xx - rx) % step == 0)
    candidates = np.argwhere(pads & near & lattice & (labels == largest))
    if candidates.size == 0:
        raise ValueError("no pad candidate satisfies the siting rules in the search radius")
    scored = []
    for iy, ix in candidates:
        field = walkback(terrain, [(int(iy), int(ix))])
        reach = int(np.count_nonzero(field.time_eps_s(rules.z_eps, rules.sigma_theta) <= rules.reach_budget_s))
        scored.append((reach, -math.hypot(iy - ry, ix - rx), int(iy), int(ix)))
    scored.sort(reverse=True)
    best = scored[0]
    ranking = [{"cell": [c[2], c[3]], "reach_cells": c[0], "distance_m": -c[1] * r} for c in scored[:10]]
    return SitingResult((best[2], best[3]), best[0], len(scored), int(pads.sum()), ranking)
