"""Display geometry helpers for RedLine polygons (proje.md §7.6, D009).

These only shape what is *drawn*: MarginField and FieldTile keep every cell.

- :func:`fill_small_holes` marks below-level pockets smaller than an area as
  inside, so contouring does not emit thousands of one-cell holes. Pockets are
  4-connected, the complement of ``find_contours(fully_connected="high")``.
- :func:`simplify_ring` is Douglas-Peucker with a distance-to-segment
  tolerance (the rule of ``skimage.measure.approximate_polygon``), compiled
  with numba because skimage's version is a Python loop.
"""
from __future__ import annotations

import numpy as np
from numba import njit
from scipy import ndimage


def fill_small_holes(work: np.ndarray, level: float, max_area_cells: float, fill_value: float) -> np.ndarray:
    """Copy of `work` where enclosed pockets of ``work < level`` with fewer than
    `max_area_cells` cells (not touching the border) are set to `fill_value`."""
    below = np.asarray(work) < level
    if max_area_cells <= 0 or not below.any():
        return np.asarray(work).copy()
    labels, count = ndimage.label(below)  # default structure: 4-connectivity
    sizes = np.bincount(labels.ravel(), minlength=count + 1)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    small = sizes < max_area_cells
    small[0] = False
    small[border] = False
    out = np.asarray(work, dtype=float).copy()
    out[small[labels]] = fill_value
    return out


@njit(cache=True)
def _dp_keep(x, y, tolerance):
    n = x.size
    keep = np.zeros(n, dtype=np.bool_)
    keep[0] = True
    keep[n - 1] = True
    stack = np.empty((n, 2), dtype=np.int64)
    top = 0
    stack[0, 0] = 0
    stack[0, 1] = n - 1
    top = 1
    while top > 0:
        top -= 1
        a = stack[top, 0]
        b = stack[top, 1]
        if b - a < 2:
            continue
        dx = x[b] - x[a]
        dy = y[b] - y[a]
        norm = np.sqrt(dx * dx + dy * dy)
        best = -1.0
        index = -1
        for i in range(a + 1, b):
            ax = x[i] - x[a]
            ay = y[i] - y[a]
            bx = x[i] - x[b]
            by = y[i] - y[b]
            if ax * dx + ay * dy > 0.0 and -(bx * dx + by * dy) > 0.0:
                d = abs(dy * ax - dx * ay) / norm  # projection inside the segment
            else:
                d = min(np.sqrt(ax * ax + ay * ay), np.sqrt(bx * bx + by * by))
            if d > best:
                best = d
                index = i
        if best > tolerance:
            keep[index] = True
            stack[top, 0] = a
            stack[top, 1] = index
            top += 1
            stack[top, 0] = index
            stack[top, 1] = b
            top += 1
    return keep


def simplify_ring(ring: np.ndarray, tolerance: float) -> np.ndarray:
    """Douglas-Peucker on an (N, 2+) closed ring; first and last points are kept."""
    ring = np.asarray(ring, dtype=float)
    if tolerance <= 0 or len(ring) < 3:
        return ring.copy()
    keep = _dp_keep(np.ascontiguousarray(ring[:, 0]), np.ascontiguousarray(ring[:, 1]), float(tolerance))
    return ring[keep]
