"""Planning-grid layers and their portable file form (proje.md §7.1, D008, D009).

`build_planning_layers` turns T1 1 m / 4 m grid-order arrays into the 4 m
planning layers exactly as D008 defines them. `save_planning_grid` writes the
layers to ``<stem>.npz`` and a JSON sidecar ``<stem>.json`` holding the npz
SHA-256, grid geometry and caller provenance; `load_planning_grid` refuses a
file whose hash does not match its sidecar. ROS nodes load this file with
numpy only (no GDAL/rasterio at runtime). The `state` layer is not stored:
orbital products know no robot observations, so it loads as UNOBSERVED and the
cell store owns every later change.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np

from .cost_human import UNOBSERVED
from .grid import Grid, block_detrended_relief, block_reduce

SCHEMA = "redline.planning_grid.v1"
STORED_LAYERS = ("z_m", "slope_deg", "slope_sigma_deg", "relief_m", "wall_slope_deg")


def build_planning_layers(dem_plan: np.ndarray, dem_fine: np.ndarray, slope5_fine: np.ndarray,
                          slope2_fine: np.ndarray, sigma_fine: np.ndarray, factor: int,
                          fine_resolution_m: float) -> dict[str, np.ndarray]:
    """D008 4 m layers from grid-order (row 0 = south) arrays.

    z = planning DEM; slope = block mean of fine slope_5m; σ = block mean of fine
    slope_sigma (one missing value keeps the block missing); wall slope = block
    max of fine slope_2m; relief = fine DEM residual range after a per-block plane.
    """
    shape = np.shape(dem_plan)
    fine = [np.shape(a) for a in (dem_fine, slope5_fine, slope2_fine, sigma_fine)]
    if any(s != (shape[0] * factor, shape[1] * factor) for s in fine):
        raise ValueError(f"fine layers {fine} must be {factor}x the planning shape {shape}")
    return {
        "z_m": np.asarray(dem_plan, dtype=float),
        "slope_deg": block_reduce(slope5_fine, factor, "mean"),
        "slope_sigma_deg": block_reduce(sigma_fine, factor, "mean"),
        "relief_m": block_detrended_relief(dem_fine, factor, fine_resolution_m),
        "wall_slope_deg": block_reduce(slope2_fine, factor, "max"),
    }


def stereo_expected_precision_m(gsd_m: float, emission_a_deg: float, emission_b_deg: float, *,
                                opposite_sides: bool, matching_px: float = 0.2) -> float:
    """Expected vertical precision of a stereo DTM, EP = ρ·GSD / (p/h) (Kirk et al. 2008).

    p/h = tan e₁ + tan e₂ when the two views lie on opposite sides of nadir, else |tan e₁ − tan e₂|.
    """
    ta, tb = math.tan(math.radians(emission_a_deg)), math.tan(math.radians(emission_b_deg))
    parallax_height = ta + tb if opposite_sides else abs(ta - tb)
    if not (gsd_m > 0 and matching_px > 0 and parallax_height > 0):
        raise ValueError("stereo precision needs positive GSD, matching precision and parallax/height")
    return matching_px * gsd_m / parallax_height


def slope_floor_deg(precision_m: float, baseline_m: float) -> float:
    """Slope error from two independent height errors over a baseline: atan(√2·EP / L)."""
    if not (precision_m >= 0 and baseline_m > 0):
        raise ValueError("precision must be >= 0 and baseline > 0")
    return math.degrees(math.atan(math.sqrt(2.0) * precision_m / baseline_m))


def _window_rms(values: np.ndarray, window_cells: int, min_valid: int = 3) -> np.ndarray:
    from scipy import ndimage

    valid = np.isfinite(values)
    num = ndimage.uniform_filter(np.where(valid, values * values, 0.0), window_cells, mode="nearest")
    den = ndimage.uniform_filter(valid.astype(float), window_cells, mode="nearest")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.sqrt(num / den)
    out[den * window_cells * window_cells < min_valid - 1e-9] = np.nan
    return out


def ensemble_slope_layers(primary_fine: np.ndarray, reference_fine: np.ndarray, factor: int, *,
                          window_cells: int, floor_deg: float) -> tuple[np.ndarray, np.ndarray, dict]:
    """Planning slope μ and its 1σ from two processings of the *same* stereo pair (D010).

    Fine slopes are averaged per planning cell for each product; D = μ_a − μ_b at cell scale.
    Their independent processing noise shows in D; the error they share (the stereo matching
    itself) does not, so it is added as the EP floor. Where both exist, μ is their mean and
    σ² = RMS_w(D)²/4 + floor²; where only the primary exists, μ is the primary and
    σ² = RMS_w(D)²/2 + floor². RMS_w is a local window RMS (window ≥ several decorrelation
    lengths). Cells with no D in the window keep σ = NaN: missing σ is never zero.
    """
    if not (window_cells >= 1 and window_cells % 2 == 1):
        raise ValueError("window_cells must be a positive odd integer")
    if not floor_deg >= 0:
        raise ValueError("floor_deg must be >= 0")
    mean_a = block_reduce(primary_fine, factor, "mean")
    mean_b = block_reduce(reference_fine, factor, "mean")
    both = np.isfinite(mean_a) & np.isfinite(mean_b)
    difference = np.where(both, mean_a - mean_b, np.nan)
    rms = _window_rms(difference, window_cells)
    # Cells beyond the reference footprint take the nearest local RMS (never zero): the
    # processing noise is a local property, so a nearby estimate beats a global fallback.
    gap = ~np.isfinite(rms) & np.isfinite(mean_a)
    filled = int(gap.sum())
    max_fill_cells = 0.0
    if gap.any() and np.isfinite(rms).any():
        from scipy import ndimage

        distance, (iy, ix) = ndimage.distance_transform_edt(~np.isfinite(rms), return_indices=True)
        rms = np.where(gap, rms[iy, ix], rms)
        max_fill_cells = float(distance[gap].max())
    mu = np.where(both, (mean_a + mean_b) / 2.0, mean_a)
    share = np.where(both, 4.0, 2.0)
    sigma = np.sqrt(rms * rms / share + floor_deg * floor_deg)
    sigma = np.where(np.isfinite(mean_a), sigma, np.nan)
    finite_d = difference[np.isfinite(difference)]
    info = {
        "both_fraction": float(both.mean()),
        "primary_only_fraction": float((np.isfinite(mean_a) & ~both).mean()),
        "sigma_missing_fraction": float(np.isnan(sigma).mean()),
        "difference_mean_deg": float(finite_d.mean()) if finite_d.size else None,
        "difference_rms_deg": float(np.sqrt((finite_d**2).mean())) if finite_d.size else None,
        "window_cells": int(window_cells),
        "floor_deg": float(floor_deg),
        "rms_filled_from_nearest_cells": filled,
        "rms_fill_max_distance_cells": max_fill_cells,
    }
    return mu, sigma, info


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_planning_grid(stem: Path | str, grid: Grid, provenance: dict) -> dict:
    """Write ``<stem>.npz`` + ``<stem>.json``; refuses to overwrite either."""
    stem = Path(stem)
    npz_path, json_path = stem.with_suffix(".npz"), stem.with_suffix(".json")
    for path in (npz_path, json_path):
        if path.exists():
            raise FileExistsError(f"{path} exists; planning grids are immutable products")
    missing = [name for name in STORED_LAYERS if name not in grid.layers]
    if missing:
        raise ValueError(f"grid is missing planning layers {missing}")
    if provenance.get("status") not in ("ARCHIVE", "DERIVED", "SIMULATED", "SCENARIO"):
        raise ValueError("provenance needs a Provenance.status")
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **{name: np.asarray(grid.layers[name], dtype=np.float32) for name in STORED_LAYERS})
    data = buffer.getvalue()
    sidecar = {
        "schema": SCHEMA,
        "npz": npz_path.name,
        "npz_sha256": _sha256(data),
        "origin_xy_m": [float(v) for v in grid.origin_xy],
        "resolution_m": float(grid.resolution_m),
        "width": int(grid.width),
        "height": int(grid.height),
        "row0": "south",
        "layers": list(STORED_LAYERS),
        "dtype": "float32",
        "provenance": provenance,
    }
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    with npz_path.open("xb") as handle:
        handle.write(data)
    with json_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n")
    return sidecar


def load_planning_grid(path: Path | str) -> tuple[Grid, dict]:
    """Load ``<stem>.npz`` (or its ``.json``) after checking the recorded SHA-256."""
    path = Path(path)
    json_path = path.with_suffix(".json")
    sidecar = json.loads(json_path.read_text(encoding="utf-8"))
    if sidecar.get("schema") != SCHEMA:
        raise ValueError(f"{json_path}: schema {sidecar.get('schema')!r} is not {SCHEMA}")
    npz_path = json_path.with_name(sidecar["npz"])
    data = npz_path.read_bytes()
    if _sha256(data) != sidecar["npz_sha256"]:
        raise ValueError(f"{npz_path}: SHA-256 does not match {json_path.name}")
    if sidecar.get("row0") != "south":
        raise ValueError("planning grids are stored in grid order (row 0 = south)")
    width, height = int(sidecar["width"]), int(sidecar["height"])
    with np.load(io.BytesIO(data), allow_pickle=False) as archive:
        if set(archive.files) != set(STORED_LAYERS):
            raise ValueError(f"{npz_path}: layers {sorted(archive.files)} are not {sorted(STORED_LAYERS)}")
        layers = {name: archive[name].astype(float) for name in STORED_LAYERS}
    layers["state"] = np.full((height, width), UNOBSERVED, dtype=np.uint8)
    origin = tuple(float(v) for v in sidecar["origin_xy_m"])
    resolution = float(sidecar["resolution_m"])
    if not all(math.isfinite(v) for v in (*origin, resolution)):
        raise ValueError("planning grid geometry must be finite")
    return Grid(origin, resolution, width=width, height=height, layers=layers), sidecar
