"""Planning grid in the local ENU `map` frame (proje.md §4.2, §7.1).

Convention (same as ROS OccupancyGrid and CellDelta.origin): `origin_xy` is the
south-west corner of cell (0, 0); layers are indexed ``[iy, ix]`` with ``iy``
increasing north (+y) and ``ix`` increasing east (+x). North-up rasters (row 0 =
north, as written by T1) must be flipped with :func:`north_up_to_grid`.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

# (dy, dx) offsets: 8-neighbourhood plus the 8 knight moves; every offset is primitive
# (gcd 1), so no edge duplicates a chain of shorter edges.
NEIGHBORS16: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 0), (0, -1), (-1, 0),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
    (1, 2), (2, 1), (2, -1), (1, -2),
    (-1, -2), (-2, -1), (-2, 1), (-1, 2),
)


def neighbors16() -> tuple[tuple[int, int], ...]:
    return NEIGHBORS16


def edge_grade(z: np.ndarray, iy: int, ix: int, dy: int, dx: int, resolution_m: float) -> float:
    """Signed grade (rise/run) of the edge from cell (iy, ix) to (iy+dy, ix+dx)."""
    run = resolution_m * math.hypot(dy, dx)
    return float((z[iy + dy, ix + dx] - z[iy, ix]) / run)


def north_up_to_grid(raster: np.ndarray) -> np.ndarray:
    """Flip a north-up raster (row 0 = north) to grid order (row 0 = south)."""
    return np.ascontiguousarray(np.asarray(raster)[::-1, :])


@dataclass(frozen=True)
class Grid:
    origin_xy: tuple[float, float]
    resolution_m: float
    width: int
    height: int
    layers: Mapping[str, np.ndarray] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (math.isfinite(self.resolution_m) and self.resolution_m > 0):
            raise ValueError("resolution_m must be positive and finite")
        if not all(math.isfinite(v) for v in self.origin_xy) or len(self.origin_xy) != 2:
            raise ValueError("origin_xy must be two finite map coordinates")
        if int(self.width) != self.width or int(self.height) != self.height or self.width < 1 or self.height < 1:
            raise ValueError("width and height must be positive integers")
        for name, layer in self.layers.items():
            if np.shape(layer) != (self.height, self.width):
                raise ValueError(
                    f"layer {name!r} has shape {np.shape(layer)}, expected {(self.height, self.width)}"
                )

    def cell_center(self, iy: int, ix: int) -> tuple[float, float]:
        x0, y0 = self.origin_xy
        return (x0 + (ix + 0.5) * self.resolution_m, y0 + (iy + 0.5) * self.resolution_m)

    def cell_index(self, x: float, y: float) -> tuple[int, int]:
        x0, y0 = self.origin_xy
        ix = math.floor((x - x0) / self.resolution_m)
        iy = math.floor((y - y0) / self.resolution_m)
        if not (0 <= ix < self.width and 0 <= iy < self.height):
            raise ValueError(f"point ({x}, {y}) is outside the grid")
        return (iy, ix)

    def layer(self, name: str) -> np.ndarray:
        try:
            return self.layers[name]
        except KeyError:
            raise ValueError(f"grid has no layer {name!r}") from None


def _blocks(a: np.ndarray, factor: int) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    if factor < 1 or a.ndim != 2 or a.shape[0] % factor or a.shape[1] % factor:
        raise ValueError(f"shape {a.shape} is not divisible by block factor {factor}")
    h, w = a.shape[0] // factor, a.shape[1] // factor
    return a.reshape(h, factor, w, factor).swapaxes(1, 2).reshape(h, w, factor * factor)


def block_reduce(a: np.ndarray, factor: int, how: str) -> np.ndarray:
    """Aggregate factor×factor blocks; a block with any missing value stays missing."""
    reducers = {"mean": np.mean, "max": np.max, "min": np.min}
    if how not in reducers:
        raise ValueError(f"unknown block reducer {how!r}")
    return reducers[how](_blocks(a, factor), axis=2)


def block_detrended_relief(z: np.ndarray, factor: int, resolution_m: float) -> np.ndarray:
    """Max-min elevation residual after a least-squares plane fit in each block.

    Removing the plane keeps a uniform slope from counting as a ridge wall.
    """
    blocks = _blocks(z, factor)
    yy, xx = np.mgrid[0:factor, 0:factor].astype(float) * resolution_m
    design = np.column_stack([np.ones(factor * factor), xx.ravel(), yy.ravel()])
    coeffs = blocks @ np.linalg.pinv(design).T
    residual = blocks - coeffs @ design.T
    return residual.max(axis=2) - residual.min(axis=2)
