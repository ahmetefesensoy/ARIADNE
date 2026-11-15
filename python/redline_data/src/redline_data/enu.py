"""Spec §4.2 local metric approximation, with explicit engineering-frame metadata.

This affine mapping is not a geodetic topocentric projection. Its GeoTIFF has
no geographic CRS: the required sidecar preserves the Mars source WKT and the
complete reversible mapping. Never label local metres EPSG:4326 or source EQC.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from pyproj import CRS, Transformer
import rasterio
from rasterio.transform import from_origin

from .crs import ExpectedCrs, check_wkt


def to_local(path: Path, *, center_lat: float, center_lon_east: float,
             h0_m: float, resolution_m: float, destination: Path,
             expected: ExpectedCrs, size_m: tuple[float, float] | None = None,
             kind: str = "dem", max_pixels: int = 25_000_000) -> dict:
    """Resample a bounded, local source window; DEM bilinear, classes nearest.

    Bounds are centred on the requested origin when size_m is supplied. Its
    dimensions must be whole output pixels; no silent change of AOI/resolution.
    Missing interpolation support stays unknown. H0 is an explicit scenario
    offset in the source elevation units, never an inferred areoid height.
    """
    path, destination = Path(path), Path(destination)
    if kind not in ("dem", "class"):
        raise ValueError("kind must be dem or class")
    if not all(math.isfinite(v) for v in (center_lat, center_lon_east, h0_m, resolution_m)):
        raise ValueError("Local frame parameters must be finite")
    if not -89 < center_lat < 89 or not 0 <= center_lon_east < 360 or resolution_m <= 0:
        raise ValueError("Invalid local origin or resolution")
    if type(max_pixels) is not int or max_pixels <= 0:
        raise ValueError("Pixel budget must be a positive integer")
    with path.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    identity = json.loads(json.dumps({"source_sha256": source_hash,
        "center_lat": center_lat, "center_lon_east": center_lon_east,
        "h0_m": h0_m, "resolution_m": resolution_m, "size_m": size_m,
        "kind": kind, "expected": asdict(expected), "algorithm": "eqc-local-v1"}))
    sidecar = destination.with_suffix(".provenance.json")
    if destination.exists() or sidecar.exists():
        if not destination.is_file() or not sidecar.is_file():
            raise ValueError("Incomplete existing ENU output; use a new path")
        previous = json.loads(sidecar.read_text(encoding="utf-8"))
        with destination.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if previous.get("identity") != identity or previous.get("sha256") != digest:
            raise ValueError("Existing ENU output differs from request/hash; use a new path")
        return previous
    with rasterio.open(path) as src:
        report = check_wkt(src.crs.to_wkt() if src.crs else None, expected)
        if src.count != 1 or src.width * src.height > max_pixels:
            raise ValueError("Expected a bounded single-band source window")
        if src.transform.b or src.transform.d or src.transform.a <= 0 or src.transform.e >= 0:
            raise ValueError("Expected a north-up, unrotated source window")
        if src.scales != (1.0,) or src.offsets != (0.0,):
            raise ValueError("Resolve source scale/offset before local elevation conversion")
        source_crs = CRS.from_wkt(report["source_wkt"])
        e0, n0 = Transformer.from_crs(source_crs.geodetic_crs, source_crs, always_xy=True).transform(
            center_lon_east, center_lat, errcheck=True)
        factor = math.cos(math.radians(center_lat)) / math.cos(math.radians(expected.lat_ts_deg))
        if size_m is None:
            left = math.ceil((src.bounds.left - e0) * factor / resolution_m) * resolution_m
            top = math.floor((src.bounds.top - n0) / resolution_m) * resolution_m
            width = math.floor(((src.bounds.right - e0) * factor - left) / resolution_m)
            height = math.floor((top - (src.bounds.bottom - n0)) / resolution_m)
        else:
            if len(size_m) != 2 or not all(math.isfinite(v) and 0 < v <= 5000 for v in size_m):
                raise ValueError("Local dimensions must be positive and at most 5000 m")
            counts = [v / resolution_m for v in size_m]
            if not all(math.isclose(v, round(v), rel_tol=0, abs_tol=1e-8) for v in counts):
                raise ValueError("Local dimensions must be whole output pixels")
            width, height = map(round, counts)
            left, top = -size_m[0] / 2, size_m[1] / 2
        if width < 1 or height < 1 or width * height > max_pixels:
            raise ValueError("Invalid output size or pixel budget exceeded")
        right, bottom = left + width * resolution_m, top - height * resolution_m
        if (left / factor + e0 < src.bounds.left - 1e-6 or right / factor + e0 > src.bounds.right + 1e-6
                or bottom + n0 < src.bounds.bottom - 1e-6 or top + n0 > src.bounds.top + 1e-6):
            raise ValueError("Local AOI is not wholly covered by the source window")
        data = np.ma.masked_invalid(src.read(1, masked=True).astype("float64")).filled(np.nan)
        transform = from_origin(left, top, resolution_m, resolution_m)
        output = np.full((height, width), np.nan, dtype="float32")
        # Map target pixel CENTRES through local→EQC→source pixel centres.
        columns = ((left + (np.arange(width) + .5) * resolution_m) / factor + e0 - src.transform.c) / src.transform.a - .5
        for start in range(0, height, 128):
            stop = min(start + 128, height)
            rows = ((top - (np.arange(start, stop) + .5) * resolution_m + n0 - src.transform.f) / src.transform.e - .5)
            rr, cc = np.broadcast_arrays(rows[:, None], columns[None, :])
            if kind == "class":
                ri, ci = np.floor(rr + .5).astype(int), np.floor(cc + .5).astype(int)
                valid = (ri >= 0) & (ri < src.height) & (ci >= 0) & (ci < src.width)
                sampled = data[np.clip(ri, 0, src.height - 1), np.clip(ci, 0, src.width - 1)]
            else:
                r0, c0 = np.floor(rr).astype(int), np.floor(cc).astype(int)
                wr, wc = rr - r0, cc - c0
                sampled = np.zeros(rr.shape)
                valid = np.ones(rr.shape, dtype=bool)
                for dr, dc, weight in ((0, 0, (1-wr)*(1-wc)), (0, 1, (1-wr)*wc),
                                       (1, 0, wr*(1-wc)), (1, 1, wr*wc)):
                    ri, ci = r0 + dr, c0 + dc
                    neighbour = data[np.clip(ri, 0, src.height-1), np.clip(ci, 0, src.width-1)]
                    needed = weight > 1e-9
                    valid &= ~needed | ((ri >= 0) & (ri < src.height) & (ci >= 0) & (ci < src.width) & np.isfinite(neighbour))
                    sampled += np.where(needed & np.isfinite(neighbour), neighbour, 0) * weight
                sampled -= h0_m
            output[start:stop] = np.where(valid, sampled, np.nan)
        if not np.isfinite(output).any():
            raise ValueError("Local output contains no valid samples")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb"):
            pass
        with rasterio.open(destination, "w", driver="GTiff", count=1, width=width, height=height,
                           dtype="float32", transform=transform, nodata=np.nan, tiled=True,
                           blockxsize=256, blockysize=256, compress="deflate") as target:
            target.write(output, 1)
            target.update_tags(FRAME="map", HORIZONTAL_UNITS="m", PROVENANCE_STATUS="DERIVED",
                               COORDINATE_METADATA=sidecar.name)
        with destination.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        result = {"identity": identity, "status": "DERIVED", "sha256": digest,
            "created_at": datetime.now(timezone.utc).isoformat(), "frame": "map", "units": "m",
            "source": str(path), "source_wkt": report["source_wkt"], "source_transform": list(src.transform),
            "origin": {"E0_m": e0, "N0_m": n0, "H0_m": h0_m, "status": "SCENARIO"},
            "east_scale_factor": factor, "shape": [height, width], "transform": list(transform),
            "resolution_m": resolution_m, "resampling": "bilinear" if kind == "dem" else "nearest",
            "nodata_fraction": float((~np.isfinite(output)).mean()),
            "vertical_reference": "source unchanged except explicit H0 offset; datum unverified",
            "alignment_verified": False,
            "scope": "spec local affine approximation; not geodetic ENU, not ground alignment validation",
            "versions": {"rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__}}
        sidecar.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return result
