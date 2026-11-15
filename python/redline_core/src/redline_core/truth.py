"""Hidden SCENARIO ground truth for SIMULATED observers (spec §6 ``scenario_rocks_<seed>.json``; D015).

The file lists sub-resolution rocks (Golombek diameters from :func:`rocks.sample_rocks`, uniform
positions, ``decor`` below 0.5 m and ``navigation`` above) and authored impassable obstacle discs
(boulder clusters, scarps). Only SIMULATED observers (the scout stub, V3 worlds) read it; the
planner, VOI and the return field must never see it.

A cell is blocked when its centre lies inside an obstacle disc or it contains a rock with
D ≥ ``d_block_m``. :func:`survey_evidence` is the scout's sensor model: features smaller than the
detection limit are not seen.
"""
from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .grid import Grid
from .rocks import sample_rocks

TRUTH_SCHEMA = "redline.scenario_rocks.v1"
NAVIGATION_D_M = 0.5
_KEYS = {"schema", "status", "site_id", "seed", "k", "d_range_m", "grid", "rocks", "obstacles", "note"}


@dataclass(frozen=True)
class Obstacle:
    obstacle_id: str
    x: float
    y: float
    radius_m: float


def scenario_world(grid: Grid, site_id: str, *, seed: int, k: float, d_range_m: tuple[float, float],
                   obstacles: Iterable[Obstacle] = (), note: str = "") -> dict:
    r = grid.resolution_m
    x0, y0 = grid.origin_xy
    width_m, height_m = grid.width * r, grid.height * r
    diameters = sample_rocks(k, width_m * height_m, d_range_m, seed) if k > 0 else np.zeros(0)
    rng = np.random.default_rng([seed, 1])  # positions: a stream independent of the diameters
    xs = x0 + rng.random(len(diameters)) * width_m
    ys = y0 + rng.random(len(diameters)) * height_m
    rocks = [{"x": float(x), "y": float(y), "d_m": float(d), "class": "navigation" if d >= NAVIGATION_D_M else "decor"}
             for x, y, d in zip(xs, ys, diameters)]
    items = [{"id": o.obstacle_id, "x": float(o.x), "y": float(o.y), "radius_m": float(o.radius_m)} for o in obstacles]
    if any(not (math.isfinite(o["radius_m"]) and o["radius_m"] > 0) for o in items):
        raise ValueError("obstacle radius must be > 0")
    return {"schema": TRUTH_SCHEMA, "status": "SCENARIO", "site_id": site_id, "seed": int(seed), "k": float(k),
            "d_range_m": [float(d_range_m[0]), float(d_range_m[1])],
            "grid": {"origin": [float(x0), float(y0)], "resolution_m": float(r), "width": grid.width,
                     "height": grid.height},
            "rocks": rocks, "obstacles": items, "note": note}


def write_truth(world: dict, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(world, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    return path


def load_truth(path: Path | str) -> dict:
    world = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(world, dict) or world.get("schema") != TRUTH_SCHEMA:
        raise ValueError(f"{path}: schema must be {TRUTH_SCHEMA!r}")
    unknown = set(world) - _KEYS
    if unknown:
        raise ValueError(f"{path}: unknown keys {sorted(unknown)}")
    if world.get("status") != "SCENARIO":
        raise ValueError(f"{path}: hidden truth must be SCENARIO")
    return world


def _cell_of(grid: Grid, x: float, y: float) -> tuple[int, int] | None:
    try:
        return grid.cell_index(x, y)
    except ValueError:
        return None


def blocked_cells(world: dict, grid: Grid, d_block_m: float) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    r = grid.resolution_m
    x0, y0 = grid.origin_xy
    for o in world["obstacles"]:
        lo_x, hi_x = math.floor((o["x"] - o["radius_m"] - x0) / r), math.floor((o["x"] + o["radius_m"] - x0) / r)
        lo_y, hi_y = math.floor((o["y"] - o["radius_m"] - y0) / r), math.floor((o["y"] + o["radius_m"] - y0) / r)
        for iy in range(max(lo_y, 0), min(hi_y, grid.height - 1) + 1):
            for ix in range(max(lo_x, 0), min(hi_x, grid.width - 1) + 1):
                cx, cy = grid.cell_center(iy, ix)
                if math.hypot(cx - o["x"], cy - o["y"]) <= o["radius_m"]:
                    cells.add((iy, ix))
    for rock in world["rocks"]:
        if rock["d_m"] >= d_block_m:
            cell = _cell_of(grid, rock["x"], rock["y"])
            if cell is not None:
                cells.add(cell)
    return cells


def _inside(polygon: Sequence[tuple[float, float]], x: float, y: float) -> bool:
    inside = False
    for (xa, ya), (xb, yb) in zip(polygon, list(polygon[1:]) + [polygon[0]]):
        if (ya > y) != (yb > y) and x < xa + (y - ya) * (xb - xa) / (yb - ya):
            inside = not inside
    return inside


def survey_evidence(world: dict, grid: Grid, polygon_xy: Sequence[tuple[float, float]], *, spacing_m: float,
                    detection_limit_m: float, d_block_m: float) -> list[tuple[float, float, float, bool]]:
    """Observations (x, y, radius_m, passable) of a survey over a polygon.

    Blocked cells inside the polygon come as small discs (one cell each); the rest of the area as
    passable discs on a ``spacing_m`` lattice. Obstacles narrower and rocks smaller than
    ``detection_limit_m`` are not seen.
    """
    polygon = [tuple(map(float, p)) for p in polygon_xy]
    seen = {**world,
            "obstacles": [o for o in world["obstacles"] if 2.0 * o["radius_m"] >= detection_limit_m],
            "rocks": [rock for rock in world["rocks"] if rock["d_m"] >= detection_limit_m]}
    out = []
    for iy, ix in sorted(blocked_cells(seen, grid, d_block_m)):
        cx, cy = grid.cell_center(iy, ix)
        if _inside(polygon, cx, cy):
            out.append((cx, cy, 0.25 * grid.resolution_m, False))
    xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
    radius = spacing_m / math.sqrt(2.0)
    for y in np.arange(min(ys) + spacing_m / 2, max(ys), spacing_m):
        for x in np.arange(min(xs) + spacing_m / 2, max(xs), spacing_m):
            if _inside(polygon, float(x), float(y)) and _cell_of(grid, float(x), float(y)) is not None:
                out.append((float(x), float(y), radius, True))
    return out
