"""Persist relative two-DTM alignment and empirical residual proxies.

No absolute datum alignment or independent uncertainty is established. Inputs
are the exact, hashed local engineering rasters produced by ``enu.to_local``.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio

from .crs import ExpectedCrs, check_wkt
from .derive import slopes
from .registration import register, shift_array


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _json(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Provenance must be a JSON object")
    return result


def _read(path: Path, resolution: float) -> tuple[dict, dict, np.ndarray]:
    meta_path = path.with_suffix(".provenance.json")
    meta = _json(meta_path)
    if meta.get("sha256") != _hash(path) or meta.get("status") != "DERIVED":
        raise ValueError(f"ENU hash/status differs: {path.name}")
    if meta.get("frame") != "map" or meta.get("units") != "m":
        raise ValueError("DEM comparison requires local metre engineering frames")
    identity = meta.get("identity", {})
    if identity.get("kind") != "dem" or not identity.get("source_sha256"):
        raise ValueError("DEM source identity is required")
    expected = identity.get("expected", {})
    check_wkt(meta.get("source_wkt"), ExpectedCrs(**expected))
    if not math.isclose(float(meta.get("resolution_m", 0)), resolution, abs_tol=1e-9):
        raise ValueError("Input resolution differs from the requested comparison grid")
    if identity.get("resolution_m") != meta["resolution_m"]:
        raise ValueError("Resolution identity differs from sidecar")
    for key in ("center_lat", "center_lon_east", "h0_m"):
        if key not in identity or not math.isfinite(identity[key]):
            raise ValueError("Finite origin mapping identity is required")
    origin = meta.get("origin", {})
    radius = expected["sphere_radius_m"]
    e0 = radius * math.radians(identity["center_lon_east"] - expected["lon_0_deg"]) * math.cos(math.radians(expected["lat_ts_deg"]))
    n0 = radius * math.radians(identity["center_lat"])
    for key, value in (("E0_m", e0), ("N0_m", n0), ("H0_m", identity["h0_m"])):
        if not math.isclose(float(origin.get(key, float("nan"))), value, abs_tol=1e-5, rel_tol=0):
            raise ValueError("Recorded origin differs from reversible source mapping")
    factor = math.cos(math.radians(identity["center_lat"])) / math.cos(math.radians(expected["lat_ts_deg"]))
    if not math.isclose(float(meta.get("east_scale_factor", 0)), factor, abs_tol=1e-12):
        raise ValueError("Recorded east scaling differs from source mapping")
    with rasterio.open(path) as src:
        if src.crs is not None or src.count != 1 or src.width * src.height > 25_000_000:
            raise ValueError("Expected bounded single-band local raster with no geographic CRS")
        if ([src.height, src.width] != meta.get("shape")
                or list(src.transform) != meta.get("transform")):
            raise ValueError("Actual raster grid differs from recorded shape/transform")
        if src.transform.b or src.transform.d or src.transform.a != resolution or src.transform.e != -resolution:
            raise ValueError("Expected square north-up metric grid")
        if src.scales != (1.0,) or src.offsets != (0.0,):
            raise ValueError("Resolve raster scale/offset before comparison")
        data = src.read(1, masked=True).astype("float64").filled(np.nan)
        data[~np.isfinite(data)] = np.nan
        profile = src.profile.copy()
    # Source windows must still match the exact identity, including product ID.
    source = Path(meta.get("source", ""))
    if not source.is_file():
        raise ValueError("Original source window is required for product provenance")
    raw = _json(source.with_suffix(".provenance.json"))
    if raw.get("sha256") != identity["source_sha256"] or _hash(source) != raw["sha256"]:
        raise ValueError("Original product window hash differs from ENU source identity")
    product_id = raw.get("identity", {}).get("product_id")
    if not isinstance(product_id, str) or not product_id:
        raise ValueError("Source product ID is required")
    source_url = raw.get("identity", {}).get("source")
    if not isinstance(source_url, str) or not source_url:
        raise ValueError("Source product URL is required")
    meta = dict(meta, source_product_id=product_id, source_url=source_url)
    return meta, profile, data


def _vertical_evidence(path: Path, primary: dict, reference: dict) -> dict:
    record = _json(path)
    products = record.get("products", {})
    verified = {}
    for meta in (primary, reference):
        product_id = meta["source_product_id"]
        entry = products.get(product_id)
        if (not isinstance(entry, dict) or entry.get("product_id") != product_id
                or entry.get("source_url") != meta["source_url"] or entry.get("units") != "m"
                or entry.get("target") != "Mars" or not entry.get("vertical_datum")
                or not entry.get("declaration_status", "").startswith("metadata_verified")):
            raise ValueError("Vertical evidence must identify each actual product URL, metre units and datum declaration")
        artifacts = entry.get("evidence")
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError("Vertical evidence requires recorded source artifacts")
        for artifact in artifacts:
            relative = artifact.get("path", "")
            if not relative or Path(relative).is_absolute():
                raise ValueError("Evidence artifact path must be relative to the evidence JSON")
            evidence_file = (path.parent / relative).resolve()
            if not evidence_file.is_relative_to(path.parent.resolve()) or not evidence_file.is_file():
                raise ValueError("Evidence source artifact is missing or escapes its directory")
            if (_hash(evidence_file) != artifact.get("sha256")
                    or evidence_file.stat().st_size != artifact.get("size_bytes")):
                raise ValueError("Evidence source artifact hash/size mismatch")
        # Preserve publisher wording and the ARD transfer limitation verbatim.
        verified[product_id] = entry
    return {"products": verified, "global_limits": record.get("global_limits", {}),
            "scope": "metadata declarations and source linkage, not realization equality"}


def _same(a: dict, b: dict, *, same_grid: bool) -> None:
    keys = ["origin", "east_scale_factor"]
    if same_grid:
        keys += ["shape", "transform", "resolution_m"]
    if any(a[key] != b[key] for key in keys):
        raise ValueError("DTM grid/origin mapping differs; reproject explicitly before comparison")
    if not same_grid:
        def bounds(meta):
            transform, shape = meta["transform"], meta["shape"]
            return (transform[2], transform[5] + shape[0]*transform[4],
                    transform[2] + shape[1]*transform[0], transform[5])
        if not np.allclose(bounds(a), bounds(b), atol=1e-7, rtol=0):
            raise ValueError("Fine and fit raster extents must describe the same physical AOI")
    for key in ("expected", "center_lat", "center_lon_east", "h0_m", "size_m"):
        if a["identity"].get(key) != b["identity"].get(key):
            raise ValueError("DTM expected CRS/AOI/origin identity differs")


def _stats(values: np.ndarray) -> dict:
    finite = values[np.isfinite(values)]
    if not finite.size:
        raise ValueError("Comparison has no common finite support")
    median = float(np.median(finite))
    return {"valid_cells": int(finite.size), "nodata_fraction": float(1 - finite.size / values.size),
            "median_m": median, "rmse_m": float(np.sqrt(np.mean(finite**2))),
            "nmad_m": float(1.4826*np.median(np.abs(finite-median)))}


def compare_dems(
    primary1m: Path, reference1m: Path, primary_fit4m: Path, reference_fit4m: Path,
    *, destination: Path, vertical_evidence: Path, max_shift_m: float = 20,
) -> dict:
    """Fit on 4 m, apply to 1 m, persist height and 5 m slope disagreement.

    Stable exposed terrain without change is an explicit scenario assumption;
    robust fitting does not establish it from the two DEMs. Vertical evidence is
    hashed and retained as an input, not interpreted as exact areoid equality.
    """
    paths = list(map(Path, (primary1m, reference1m, primary_fit4m, reference_fit4m)))
    evidence = Path(vertical_evidence)
    loaded = [_read(path, resolution) for path, resolution in zip(paths, (1, 1, 4, 4))]
    p, r, pf, rf = [value[0] for value in loaded]
    _same(p, r, same_grid=True)
    _same(pf, rf, same_grid=True)
    _same(p, pf, same_grid=False)
    _same(r, rf, same_grid=False)
    for fine, coarse in ((p, pf), (r, rf)):
        if (fine["identity"]["source_sha256"] != coarse["identity"]["source_sha256"]
                or fine["source_product_id"] != coarse["source_product_id"]):
            raise ValueError("Fit and full-resolution rasters must share the exact source product")
    if p["identity"]["source_sha256"] == r["identity"]["source_sha256"] or p["source_product_id"] == r["source_product_id"]:
        raise ValueError("Comparison requires two distinct source products, not one resampled twice")
    evidence_record = _vertical_evidence(evidence, p, r)
    inputs = {str(path): {"sha256": meta["sha256"], "metadata_sha256": _hash(path.with_suffix(".provenance.json"))}
              for path, (meta, _profile, _array) in zip(paths, loaded)}
    identity = {"inputs": inputs, "vertical_evidence": {"path": str(evidence), "sha256": _hash(evidence)},
                "max_shift_m": max_shift_m, "algorithm": "two-dtm-relative-comparison-v1"}
    destination = Path(destination)
    bundle_path = destination / "comparison.provenance.json"
    if bundle_path.exists():
        previous = _json(bundle_path)
        if previous.get("identity") != identity:
            raise ValueError("Existing comparison has a different request identity")
        expected_files = {bundle_path.name}
        for artifact in previous["assets"].values():
            path = destination / artifact["href"]
            sidecar = path.with_suffix(".provenance.json")
            expected_files.update((path.name, sidecar.name))
            if (_hash(path) != artifact["sha256"] or _hash(sidecar) != artifact["metadata_sha256"]
                    or _json(sidecar) != previous["metadata"][sidecar.name]):
                raise ValueError("Existing comparison artifact or metadata hash differs")
        if {f.name for f in destination.iterdir()} != expected_files:
            raise ValueError("Existing comparison contains unexpected files")
        return previous
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Incomplete/nonempty comparison destination; use a new path")
    fit = register(loaded[2][2], loaded[3][2], 4, max_shift_m, grids_verified=True)
    fit_summary = {key: value for key, value in fit.items() if key != "aligned_reference"}
    a, b = loaded[0][2], loaded[1][2]
    aligned = shift_array(b, fit["shift_east_m"], fit["shift_north_m"], 1) + fit["vertical_offset_removed_m"]
    residual = a - aligned
    before = a - b
    # Evaluate before/after on identical common support, not changing masks.
    shared = np.isfinite(before) & np.isfinite(residual)
    before_shared, after_shared = np.where(shared, before, np.nan), np.where(shared, residual, np.nan)
    slope_primary, slope_reference = slopes(a, 1, (5,))[5], slopes(aligned, 1, (5,))[5]
    slope_proxy = np.abs(slope_primary - slope_reference)
    if not np.isfinite(slope_proxy).any():
        raise ValueError("No common 5 m slope support after registration")
    created = datetime.now(timezone.utc).isoformat()
    destination.mkdir(parents=True, exist_ok=True)
    layers = {"aligned_reference": (aligned, "m"), "dtm_residual_m": (residual, "m"),
              "slope_sigma": (slope_proxy, "degree")}
    assets, metadata = {}, {}
    for name, (values, unit) in layers.items():
        target = destination / f"{name}.tif"
        sidecar = target.with_suffix(".provenance.json")
        profile = dict(loaded[0][1], dtype="float32", crs=None, nodata=np.nan, compress="deflate")
        with target.open("xb"):
            pass
        with rasterio.open(target, "w", **profile) as dst:
            dst.write(values.astype("float32"), 1)
            dst.update_tags(FRAME="map", UNITS=unit, PROVENANCE_STATUS="DERIVED", COORDINATE_METADATA=sidecar.name)
        meta = {key: p[key] for key in ("source_wkt", "origin", "east_scale_factor", "shape", "transform", "resolution_m")}
        meta.update({"identity": identity, "sha256": _hash(target), "status": "DERIVED", "created_at": created,
            "frame": "map", "units": unit, "alignment_verified": False,
            "relative_registration_accepted": True,
            "vertical_reference": {"primary": evidence_record["products"][p["source_product_id"]]["vertical_datum"],
                                   "reference": evidence_record["products"][r["source_product_id"]]["vertical_datum"],
                                   "realization_equality_verified": False},
            "vertical_evidence": evidence_record,
            "interpretation": "absolute 5 m slope disagreement proxy, not independent one-sigma" if unit == "degree" else "relative DTM empirical comparison, not independent height accuracy",
            "registration": fit_summary})
        with sidecar.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(meta, indent=2, allow_nan=False) + "\n")
        assets[name] = {"href": target.name, "sha256": meta["sha256"], "unit": unit,
                        "metadata": sidecar.name, "metadata_sha256": _hash(sidecar),
                        "nodata_fraction": float((~np.isfinite(values)).mean())}
        metadata[sidecar.name] = meta
    result = {"identity": identity, "status": "DERIVED", "created_at": created,
        "assets": assets, "metadata": metadata, "registration": fit_summary,
        "vertical_evidence": evidence_record,
        "before_shared": _stats(before_shared), "after_shared": _stats(after_shared),
        "full_primary_nodata_fraction": float((~np.isfinite(a)).mean()),
        "full_reference_nodata_fraction": float((~np.isfinite(b)).mean()),
        "slope_disagreement": {"unit": "degree", "baseline_m": 5,
            "definition": "abs(slope5m(primary)-slope5m(aligned_reference))",
            "interpretation": "empirical disagreement proxy, NOT independent one-sigma uncertainty"},
        "unknowns": ["exact MOLA areoid realization/version and equality",
                     "shared control/correlated errors", "independent ground accuracy",
                     "stable exposed terrain/no surface change assumed, not established by robust fit"],
        "milestone_T1_complete": False,
        "scope": "relative numerical comparison only; overall T1 acceptance is decided by QA"}
    with bundle_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result
