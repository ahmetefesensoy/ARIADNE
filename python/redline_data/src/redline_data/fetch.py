"""Bounded window extraction with source CRS, mask and provenance preserved."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import warnings
from urllib.request import Request, urlopen

import numpy as np
from pyproj import CRS, Transformer
import rasterio
from rasterio.windows import Window, from_bounds

from redline_data.crs import ExpectedCrs, check_wkt


@dataclass(frozen=True)
class WindowRequest:
    site_id: str
    center_lat: float
    center_lon_east: float
    size_m: tuple[float, float]

    def __post_init__(self):
        if not self.site_id or not self.site_id.replace("_", "").isalnum():
            raise ValueError("Site id must be a simple identifier")
        if not math.isfinite(self.center_lat) or not -89 < self.center_lat < 89:
            raise ValueError("Invalid nonpolar site latitude")
        if not math.isfinite(self.center_lon_east) or not 0 <= self.center_lon_east < 360:
            raise ValueError("Expected east-positive longitude in [0,360)")
        if len(self.size_m) != 2 or not all(math.isfinite(v) and 0 < v <= 5000 for v in self.size_m):
            raise ValueError("Window dimensions must be positive and at most 5000 m")


def confirm_http_range(url: str, timeout_s: float = 20) -> dict:
    """Read at most 16 bytes; abort immediately if server ignores Range."""
    if not url.startswith("https://"):
        raise ValueError("Remote rasters require HTTPS")
    request = Request(url, headers={"Range": "bytes=0-15", "User-Agent": "REDLINE-data/0.1"})
    with urlopen(request, timeout=timeout_s) as response:
        content_range = response.headers.get("Content-Range", "")
        matched_range = re.fullmatch(r"bytes 0-15/([0-9]+)", content_range)
        if response.status != 206 or matched_range is None or int(matched_range[1]) <= 15:
            raise ValueError("Source did not honor bounded HTTP Range; no full download permitted")
        header = response.read(16)
        if len(header) != 16 or header[:4] not in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
            raise ValueError("Range response does not contain a TIFF header")
        if header[:4] in (b"II+\x00", b"MM\x00+"):
            endian = "little" if header[:2] == b"II" else "big"
            if int.from_bytes(header[4:6], endian) != 8 or header[6:8] != b"\x00\x00":
                raise ValueError("Range response does not contain a supported BigTIFF header")
        return {"status": 206, "content_range": response.headers["Content-Range"],
                "etag": response.headers.get("ETag"), "sample_bytes": 16}


def site_bounds(crs: CRS, request: WindowRequest) -> tuple[float, float, float, float]:
    """Return projected source bounds for a local metric box (§4.2)."""
    transformer = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    east, north = transformer.transform(request.center_lon_east, request.center_lat, errcheck=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        latitude_true_scale = float(crs.to_dict().get("lat_ts", 0))
    half_east = (request.size_m[0] * math.cos(math.radians(latitude_true_scale))
                 / (2 * math.cos(math.radians(request.center_lat))))
    half_north = request.size_m[1] / 2
    return east-half_east, north-half_north, east+half_east, north+half_north


def extract_window(source: str, request: WindowRequest, expected: ExpectedCrs,
                   destination: Path, *, product_id: str,
                   max_pixels: int = 25_000_000,
                   max_source_block_bytes: int = 512_000_000) -> dict:
    """Extract one source-aligned DEM band, never a full remote mosaic.

    Existing artifacts are accepted only when request, source and file hash
    match. A change requires a new output path, preserving the previous run.
    """
    destination = Path(destination)
    if not product_id:
        raise ValueError("A source product id is required")
    if any(type(v) is not int or v <= 0 for v in (max_pixels, max_source_block_bytes)):
        raise ValueError("Read budgets must be positive")
    metadata_path = destination.with_suffix(".provenance.json")
    identity = {"source": source, "product_id": product_id, "request": asdict(request),
                "expected_crs": asdict(expected)}
    # Normalize tuple/list representation for comparison after JSON roundtrip.
    identity = json.loads(json.dumps(identity))
    if destination.exists() or metadata_path.exists():
        if not destination.is_file() or not metadata_path.is_file():
            raise ValueError("Incomplete existing window; use a new output path")
        previous = json.loads(metadata_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if previous.get("identity") != identity or previous.get("sha256") != digest:
            raise ValueError("Existing artifact differs from request/hash; use a new output path")
        return previous
    remote = source.startswith(("https://", "http://"))
    range_evidence = confirm_http_range(source) if remote else None
    options = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="20",
                   GDAL_HTTP_CONNECTTIMEOUT="10", GDAL_HTTP_MAX_RETRY="2",
                   GDAL_HTTP_RETRY_DELAY="1", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff")
    with rasterio.Env(**options), rasterio.open(source) as src:
        report = check_wkt(src.crs.to_wkt() if src.crs else None, expected)
        if src.count != 1:
            raise ValueError("DEM window extractor expects one elevation band")
        if src.transform.b != 0 or src.transform.d != 0 or src.transform.a <= 0 or src.transform.e >= 0:
            raise ValueError("Source must be a north-up, unrotated raster")
        bounds = site_bounds(CRS.from_wkt(report["source_wkt"]), request)
        fractional = from_bounds(*bounds, transform=src.transform)
        col, row = math.floor(fractional.col_off), math.floor(fractional.row_off)
        right = math.ceil(fractional.col_off + fractional.width)
        bottom = math.ceil(fractional.row_off + fractional.height)
        window = Window(col, row, right-col, bottom-row)
        if col < 0 or row < 0 or right > src.width or bottom > src.height:
            raise ValueError("Requested site is not wholly covered by source raster bounds")
        if window.width * window.height > max_pixels:
            raise ValueError("Requested window exceeds pixel memory budget")
        # Window reads touch whole compressed source blocks. Gale v3 is a
        # row-stripped TIFF, not a tiled COG, so a narrow AOI still touches full
        # source rows. Bound that decoded block volume explicitly as well.
        block_rows, block_cols = src.block_shapes[0]
        blocks_y = math.ceil(bottom/block_rows) - math.floor(row/block_rows)
        blocks_x = math.ceil(right/block_cols) - math.floor(col/block_cols)
        block_bytes = blocks_y * blocks_x * block_rows * block_cols * np.dtype(src.dtypes[0]).itemsize
        if block_bytes > max_source_block_bytes:
            raise ValueError("Window touches too many decoded source block bytes; reduce AOI or choose tiled product")
        data = src.read(1, window=window, masked=True).astype("float32")
        data = np.ma.masked_invalid(data)
        if data.count() == 0:
            raise ValueError("Requested window contains no valid elevation samples")
        profile = dict(driver="GTiff", width=int(window.width), height=int(window.height),
                       count=1, dtype="float32", nodata=float("nan"), crs=src.crs,
                       transform=src.window_transform(window), tiled=True,
                       blockxsize=256, blockysize=256, compress="deflate")
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Never silently replace a previously created output.
        with destination.open("xb"):
            pass
        try:
            with rasterio.open(destination, "w", **profile) as output:
                output.write(data.filled(np.nan), 1)
                output.update_tags(PROVENANCE_STATUS="DERIVED", SOURCE_PRODUCT_ID=product_id,
                                   SOURCE_URL=source, ELEVATION_UNITS="unverified; inspect source label")
            result = {
                "identity": identity, "status": "DERIVED", "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "created_at": datetime.now(timezone.utc).isoformat(), "range_probe": range_evidence,
                "source_shape": [src.height, src.width], "shape": list(data.shape),
                "source_block_shape": [block_rows, block_cols],
                "decoded_source_block_bytes_budget_estimate": block_bytes,
                "source_is_tiled": bool(src.profile.get("tiled")),
                "source_window": [col, row, int(window.width), int(window.height)],
                "source_transform": list(src.transform), "transform": list(profile["transform"]),
                "crs_report": report, "nodata_fraction": float(np.ma.getmaskarray(data).mean()),
                "source_scales": list(src.scales), "source_offsets": list(src.offsets),
                "source_band_units": list(src.units), "source_tags": src.tags(),
                "versions": {"rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__},
                "scope": "Source-aligned window only; no ENU warp, vertical datum or pixel/target alignment verified",
            }
            metadata_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            return result
        except Exception:
            # Leave any partial artifact visible. Next run refuses it rather than
            # confusing it with an accepted, hashed result.
            raise
