"""Metric DEM derivatives with explicit support and missing-data policies.

Callers must establish the CRS, square pixel spacing, elevation units (metres),
and common raster grid before supplying arrays. Array shape alone proves none
of these. Functions do not fill missing cells or extrapolate at raster edges.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _dem(values: ArrayLike) -> NDArray[np.float64]:
    if np.iscomplexobj(values):
        raise ValueError("DEM elevations must be real numbers in metres")
    data = np.ma.asarray(values, dtype=np.float64).filled(np.nan)
    if data.ndim != 2 or min(data.shape) < 3:
        raise ValueError("DEM must be a two-dimensional grid at least 3 by 3")
    return np.where(np.isfinite(data), data, np.nan)


def _positive_metres(value: float, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be finite and positive, in metres")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive, in metres")
    return value


def slopes(
    dem: ArrayLike,
    resolution_m: float,
    baselines_m: Iterable[float] = (2, 5),
) -> dict[float, NDArray[np.float64]]:
    """Return slope magnitude in degrees for each symmetric physical baseline.

    A baseline is the TOTAL distance between samples: 2 m on a 1 m grid uses
    values at x/y +/-1 m. At a fractional pixel position, the endpoint elevation
    is linearly interpolated between its two actual neighbours; the derivative
    denominator remains the requested physical baseline. This does not create
    resolving power beyond the input DEM.

    Baselines shorter than twice the pixel spacing are rejected: a 4 m planning
    grid cannot supply 2 m or 5 m terrain slopes. Derive these from the source
    grid first. All cells along each derivative's cross-shaped support must be
    finite, including the centre. Edges without full support remain NaN.
    """
    data = _dem(dem)
    resolution = _positive_metres(resolution_m, "resolution_m")
    baselines = [_positive_metres(value, "baseline") for value in baselines_m]
    if not baselines or len(set(baselines)) != len(baselines):
        raise ValueError("Provide at least one distinct baseline")
    result = {}
    height, width = data.shape
    for baseline in baselines:
        if baseline < 2 * resolution and not math.isclose(
            baseline, 2 * resolution, rel_tol=1e-12
        ):
            raise ValueError("Each baseline must be at least twice the grid resolution")
        half_pixels = baseline / (2 * resolution)
        if math.isclose(half_pixels, round(half_pixels), abs_tol=1e-12, rel_tol=0):
            half_pixels = float(round(half_pixels))
        reach = math.ceil(half_pixels)
        if min(height, width) <= 2 * reach:
            raise ValueError(f"Baseline {baseline:g} m has no full support in this DEM")
        rows = slice(reach, height - reach)
        columns = slice(reach, width - reach)
        valid = np.ones((height - 2 * reach, width - 2 * reach), dtype=bool)
        for offset in range(-reach, reach + 1):
            valid &= np.isfinite(data[rows, reach + offset:width - reach + offset])
            valid &= np.isfinite(data[reach + offset:height - reach + offset, columns])

        def sample(offset: float, axis: int) -> NDArray[np.float64]:
            low = math.floor(offset)
            weight = offset - low

            def shifted(index: int) -> NDArray[np.float64]:
                if axis == 1:
                    return data[rows, reach + index:width - reach + index]
                return data[reach + index:height - reach + index, columns]

            first = shifted(low)
            return first if weight == 0 else (1 - weight) * first + weight * shifted(low + 1)

        dx = (sample(half_pixels, 1) - sample(-half_pixels, 1)) / baseline
        dy = (sample(half_pixels, 0) - sample(-half_pixels, 0)) / baseline
        output = np.full(data.shape, np.nan)
        output[rows, columns] = np.where(valid, np.degrees(np.arctan(np.hypot(dx, dy))), np.nan)
        result[baseline] = output
    return result


def roughness(
    dem: ArrayLike, resolution_m: float, *, radius_m: float = 2
) -> NDArray[np.float64]:
    """RMS elevation residual to a least-squares local plane, in metres.

    The support is a square with radius_m on each axis. Its radius must be an
    integer pixel count, at least one. A tilted plane has zero roughness. Any
    missing cell in the square invalidates that output cell; edges remain NaN.
    This defined geometric metric is not an instrument noise/accuracy estimate.
    """
    data = _dem(dem)
    resolution = _positive_metres(resolution_m, "resolution_m")
    radius = _positive_metres(radius_m, "radius_m")
    pixels = radius / resolution
    if pixels < 1 or not math.isclose(pixels, round(pixels), abs_tol=1e-12, rel_tol=0):
        raise ValueError("radius_m must be at least one whole grid pixel")
    reach = round(pixels)
    height, width = data.shape
    if min(height, width) <= 2 * reach:
        raise ValueError("Roughness support does not fit in this DEM")
    rows, columns = slice(reach, height - reach), slice(reach, width - reach)
    centre = data[rows, columns]
    valid = np.isfinite(centre)
    sum_z = np.zeros(centre.shape)
    sum_z2 = np.zeros(centre.shape)
    sum_xz = np.zeros(centre.shape)
    sum_yz = np.zeros(centre.shape)
    sum_x2 = 0.0
    # Coordinates are symmetric so the plane's normal matrix is diagonal.
    # Subtracting the centre first avoids cancellation from absolute elevations.
    for iy in range(-reach, reach + 1):
        for ix in range(-reach, reach + 1):
            delta = data[
                reach + iy:height - reach + iy,
                reach + ix:width - reach + ix,
            ] - centre
            valid &= np.isfinite(delta)
            delta = np.where(np.isfinite(delta), delta, 0)
            x, y = ix * resolution, iy * resolution
            sum_z += delta
            sum_z2 += delta * delta
            sum_xz += x * delta
            sum_yz += y * delta
            sum_x2 += x * x
    count = (2 * reach + 1) ** 2
    residual_sum = sum_z2 - sum_z * sum_z / count
    residual_sum -= (sum_xz * sum_xz + sum_yz * sum_yz) / sum_x2
    rms = np.sqrt(np.maximum(residual_sum / count, 0))
    output = np.full(data.shape, np.nan)
    output[rows, columns] = np.where(valid, rms, np.nan)
    return output


def sigma(
    dem: ArrayLike,
    reference: ArrayLike | None = None,
    *,
    alignment_verified: bool = False,
) -> dict:
    """Compare two DTMs after removing their median vertical difference.

    ``alignment_verified`` is an explicit caller precondition, not a substitute
    for checking both rasters' CRS, affine transform, registration, resolution,
    elevation units and vertical reference. This function cannot check metadata
    hidden by array inputs, and removes NO horizontal shift or tilt.

    residual_m = (dem-reference) - median(dem-reference) on common valid cells.
    sigma_proxy_m = abs(residual_m) is labelled empirical disagreement ONLY:
    shared control and correlated errors prevent treating it as independent
    one-sigma accuracy. The proxy's unit is metres, not slope degrees.
    A missing second DTM or fewer than three overlapping cells is an error.
    """
    if reference is None:
        raise ValueError("A second DTM is required; uncertainty cannot be invented")
    if alignment_verified is not True:
        raise ValueError("Verify full grid/vertical alignment before comparing DTMs")
    first, second = _dem(dem), _dem(reference)
    if first.shape != second.shape:
        raise ValueError("Aligned DTM arrays must have identical shapes")
    valid = np.isfinite(first) & np.isfinite(second)
    count = int(valid.sum())
    if count < 3:
        raise ValueError("At least three common valid DTM cells are required")
    differences = first[valid] - second[valid]
    offset = float(np.median(differences))
    residual = np.full(first.shape, np.nan)
    residual[valid] = differences - offset
    return {
        "residual_m": residual,
        "sigma_proxy_m": np.abs(residual),
        "vertical_offset_removed_m": offset,
        "overlap_cells": count,
        "rmse_residual_m": float(np.sqrt(np.mean(residual[valid] ** 2))),
        "median_absolute_residual_m": float(np.median(np.abs(residual[valid]))),
        "unit": "m",
        "interpretation": "empirical DTM disagreement, not independent one-sigma accuracy",
        "horizontal_registration": "verified by caller, not estimated here",
    }


def write_products(path: Path, destination: Path, *, baselines_m=(2, 5), radius_m=2) -> dict:
    """Persist metric derivatives of a verified local-frame DEM and their hashes.

    A missing second registered DTM is recorded explicitly. No sigma raster is
    substituted with zeros, roughness, or a made-up constant.
    """
    import rasterio

    path, destination = Path(path), Path(destination)
    with path.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    source_meta_path = path.with_suffix(".provenance.json")
    metadata = json.loads(source_meta_path.read_text(encoding="utf-8"))
    if metadata.get("sha256") != source_hash or metadata.get("frame") != "map" or metadata.get("units") != "m":
        raise ValueError("DEM must have matching local-frame metre provenance")
    identity = {"source_sha256": source_hash, "baselines_m": list(baselines_m),
                "roughness_radius_m": radius_m, "algorithm": "terrain-derivatives-v1"}
    manifest_path = destination / "derivatives.provenance.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous.get("identity") != identity:
            raise ValueError("Existing derivatives have a different request")
        for artifact in previous["assets"].values():
            with (destination / artifact["href"]).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != artifact["sha256"]:
                    raise ValueError("Existing derivative hash differs")
        return previous
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Incomplete/nonempty derivative directory; use a new path")
    with rasterio.open(path) as src:
        if src.count != 1 or src.width * src.height > 25_000_000:
            raise ValueError("Expected a bounded single-band DEM")
        if src.transform.b or src.transform.d or src.transform.a <= 0 or not math.isclose(src.transform.a, -src.transform.e):
            raise ValueError("Expected square north-up local grid")
        resolution = src.transform.a
        data = src.read(1, masked=True)
        layers = {f"slope_{baseline:g}m": (values, "degree")
                  for baseline, values in slopes(data, resolution, baselines_m).items()}
        layers["roughness"] = (roughness(data, resolution, radius_m=radius_m), "m")
        if any(not np.isfinite(values).any() for values, _unit in layers.values()):
            raise ValueError("Derivative has no valid support")
        profile = src.profile.copy()
    destination.mkdir(parents=True, exist_ok=True)
    assets = {}
    for name, (values, unit) in layers.items():
        target_path = destination / f"{name}.tif"
        with target_path.open("xb"):
            pass
        profile.update(dtype="float32", nodata=np.nan, compress="deflate")
        with rasterio.open(target_path, "w", **profile) as target:
            target.write(values.astype("float32"), 1)
            target.update_tags(FRAME="map", UNITS=unit, PROVENANCE_STATUS="DERIVED",
                               SOURCE_SHA256=source_hash)
        with target_path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        finite = values[np.isfinite(values)]
        assets[name] = {"href": target_path.name, "sha256": digest, "unit": unit,
            "nodata_fraction": float((~np.isfinite(values)).mean()),
            "min": float(finite.min()), "max": float(finite.max()), "mean": float(finite.mean())}
    result = {"identity": identity, "status": "DERIVED", "source": str(path),
        "created_at": datetime.now(timezone.utc).isoformat(), "assets": assets,
        "resolution_m": resolution, "frame": "map",
        "slope_method": "symmetric endpoint difference; total physical baseline; fractional endpoints linear",
        "roughness_method": "RMS residual to local least-squares plane, square support",
        "sigma": {"available": False, "reason": "second horizontally/vertically registered DTM not supplied"}}
    manifest_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result
