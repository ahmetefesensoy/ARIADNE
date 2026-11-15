"""Candidate science targets from terrain (D011).

Boxwork ridges stand above their surroundings and hollows sit below, so the topographic
position index TPI = z − mean(z in an annulus) separates the two classes. Targets are the
strongest TPI extrema of each class among *eligible* planning cells (walkable, workable
slope, inside the return-time reach), at least ``min_spacing_m`` apart. They are SCENARIO
targets derived from DERIVED terrain; composition is not observed here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage


def topographic_position_index(z: np.ndarray, resolution_m: float, inner_m: float, outer_m: float) -> np.ndarray:
    """z minus the mean of an annulus inner_m < r ≤ outer_m (NaN-aware)."""
    if not 0 <= inner_m < outer_m:
        raise ValueError("annulus needs 0 <= inner < outer")
    reach = int(np.ceil(outer_m / resolution_m))
    yy, xx = np.mgrid[-reach:reach + 1, -reach:reach + 1] * resolution_m
    r = np.hypot(yy, xx)
    kernel = ((r > inner_m) & (r <= outer_m)).astype(float)
    valid = np.isfinite(z)
    num = ndimage.convolve(np.where(valid, z, 0.0), kernel, mode="constant")
    den = ndimage.convolve(valid.astype(float), kernel, mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        tpi = z - num / den
    tpi[(den < 0.5 * kernel.sum()) | ~valid] = np.nan
    return tpi


@dataclass(frozen=True)
class Target:
    target_id: str
    science_class: str
    cell: tuple[int, int]
    tpi_m: float


def pick_targets(tpi_cells: np.ndarray, eligible: np.ndarray, resolution_m: float, *, per_class: int,
                 min_spacing_m: float, min_abs_tpi_m: float, prefix: str = "T") -> list[Target]:
    """Strongest ridges (TPI > 0) and hollows (TPI < 0), greedily spaced."""
    out: list[Target] = []
    chosen: list[tuple[int, int]] = []
    for cls, sign in (("ridge", 1.0), ("hollow", -1.0)):
        score = np.where(eligible & np.isfinite(tpi_cells), sign * tpi_cells, -np.inf)
        order = np.argsort(score, axis=None)[::-1]
        count = 0
        for flat in order:
            if count >= per_class or not np.isfinite(score.flat[flat]) or score.flat[flat] < min_abs_tpi_m:
                break
            cell = tuple(int(v) for v in np.unravel_index(flat, score.shape))
            if any(np.hypot(cell[0] - c[0], cell[1] - c[1]) * resolution_m < min_spacing_m for c in chosen):
                continue
            chosen.append(cell)
            count += 1
            out.append(Target(f"{prefix}{len(out) + 1:02d}", cls, cell, float(tpi_cells[cell])))
    return out
