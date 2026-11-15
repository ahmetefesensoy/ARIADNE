#!/usr/bin/env python3
"""Bounded, read-only original PDS IMG -> local ARD pixel diagnostic.

Fetches one 16 KiB PDS label prefix and three 8x8 source windows. GDAL only
opens the in-memory label and a local TIFF; it never receives a remote URL.
JSON is written to stdout. No source data or local files are modified.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.warp import reproject, transform
from rasterio.windows import Window


PRODUCT_ID = "DTEEC_019698_1750_019988_1750_U01"
ORIGINAL_URL = (
    "https://www.uahirise.org/PDS/DTM/ESP/ORB_019600_019699/"
    "ESP_019698_1750_ESP_019988_1750/" + PRODUCT_ID + ".IMG"
)
ARD_URL = (
    "https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/"
    "controlled/dtm/ESP_019698_1750_ESP_019988_1750/" + PRODUCT_ID + ".tif"
)
TOLERANCE_M = 0.1  # Fixed before observing residuals; numeric transfer only.
BODY_BUDGET_BYTES = 1_000_000
WINDOW_SIDE = 8


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


class BoundedRangeReader:
    def __init__(self, url: str):
        self.url = url
        self.bytes_read = 0
        self.etag: str | None = None
        self.total_size: int | None = None
        self.requests: list[dict] = []

    def read(self, start: int, length: int) -> bytes:
        if start < 0 or length <= 0:
            raise ValueError("Invalid range")
        if self.bytes_read + length > BODY_BUDGET_BYTES:
            raise RuntimeError("Original IMG HTTP body budget exceeded")
        end = start + length - 1
        headers = {
            "User-Agent": "REDLINE-T1-bounded-transfer-probe/1.0",
            "Range": f"bytes={start}-{end}",
            "Accept-Encoding": "identity",
        }
        if self.etag:
            headers["If-Match"] = self.etag
        request = urllib.request.Request(self.url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            # Inspect response headers before reading any body. No fallback
            # to a complete IMG download is permitted.
            if response.status != 206:
                raise RuntimeError("Aborted: original server did not return 206")
            match = re.fullmatch(
                r"bytes (\d+)-(\d+)/(\d+)",
                response.headers.get("Content-Range", ""),
            )
            if not match or tuple(map(int, match.groups()[:2])) != (start, end):
                raise RuntimeError("Aborted: unexpected Content-Range")
            total = int(match.group(3))
            if self.total_size is not None and total != self.total_size:
                raise RuntimeError("Source size changed between requests")
            self.total_size = total
            if int(response.headers.get("Content-Length", "-1")) != length:
                raise RuntimeError("Aborted: unexpected Content-Length")
            if response.headers.get("Content-Encoding", "identity") != "identity":
                raise RuntimeError("Aborted: encoded byte range")
            etag = response.headers.get("ETag")
            if not etag or (self.etag and etag != self.etag):
                raise RuntimeError("Source ETag missing or changed")
            self.etag = etag
            body = response.read(length + 1)
            self.bytes_read += len(body)
            if len(body) != length:
                raise RuntimeError("Aborted: unexpected range body size")
            self.requests.append(
                {
                    "requested_url": self.url,
                    "final_url": response.url,
                    "status": response.status,
                    "range": headers["Range"],
                    "content_range": response.headers["Content-Range"],
                    "etag": etag,
                    "last_modified": response.headers.get("Last-Modified"),
                    "observed_at_utc": utc_now(),
                    "body_bytes": len(body),
                    "body_sha256": hashlib.sha256(body).hexdigest(),
                }
            )
            return body


def integer_keyword(label: str, name: str) -> int:
    match = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*=\s*(\d+)\s*$", label)
    if not match:
        raise ValueError("Missing unambiguous integer PDS keyword: " + name)
    return int(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ard-crop", type=Path, required=True)
    args = parser.parse_args()
    reader = BoundedRangeReader(ORIGINAL_URL)
    prefix = reader.read(0, 16384)
    label = prefix.split(b"\x00", 1)[0].decode("ascii")
    if not re.search(r"(?m)^END\s*$", label):
        raise RuntimeError("PDS label is not complete in bounded prefix")
    if not re.search(r'(?m)^PRODUCT_ID\s*=\s*"' + PRODUCT_ID + r'"\s*$', label):
        raise RuntimeError("Wrong original product ID")
    if not re.search(r'(?m)^TARGET_NAME\s*=\s*"MARS"\s*$', label):
        raise RuntimeError("Original label target is not MARS")
    if not re.search(r"(?m)^\s*SAMPLE_TYPE\s*=\s*PC_REAL\s*$", label):
        raise RuntimeError("This probe requires little-endian PC_REAL")
    if integer_keyword(label, "SAMPLE_BITS") != 32:
        raise RuntimeError("This probe requires Float32 samples")
    record_bytes = integer_keyword(label, "RECORD_BYTES")
    image_record = integer_keyword(label, "^IMAGE")
    image_offset = (image_record - 1) * record_bytes

    # PDS VirtualIO reads source-specific CRS, geotransform, scale, offset,
    # and sentinel from the actual label. It has no network access here.
    with MemoryFile(prefix, filename="original.IMG") as memory:
        with memory.open() as original:
            source_crs = original.crs
            source_transform = original.transform
            width, height = original.width, original.height
            scale, offset = original.scales[0], original.offsets[0]
            nodata = original.nodata
            if original.driver != "PDS" or original.dtypes != ("float32",):
                raise RuntimeError("Unexpected PDS metadata driver/dtype")
    if record_bytes != width * 4:
        raise RuntimeError("Unsupported row padding or record layout")
    if reader.total_size != image_offset + height * record_bytes:
        raise RuntimeError("PDS layout does not match actual HTTP file size")
    source_params = source_crs.to_dict()
    if source_params.get("proj") != "eqc" or source_params.get("units") != "m":
        raise RuntimeError("Expected source spherical EQC in metres")

    with rasterio.open(args.ard_crop) as ard:
        if ard.tags().get("SOURCE_PRODUCT_ID") != PRODUCT_ID:
            raise RuntimeError("Wrong local ARD product ID")
        if ard.tags().get("SOURCE_URL") != ARD_URL:
            raise RuntimeError("Unexpected local ARD source URL")
        if ard.dtypes != ("float32",) or ard.scales != (1.0,) or ard.offsets != (0.0,):
            raise RuntimeError("Local crop must retain unscaled Float32 heights")
        destination_crs = ard.crs
        destination_transform = ard.transform
        fractions = ((0.2, 0.2), (0.5, 0.8), (0.8, 0.4))
        points = []
        for index, (row_fraction, col_fraction) in enumerate(fractions, start=1):
            row, col = int(ard.height * row_fraction), int(ard.width * col_fraction)
            target_window = Window(col, row, 1, 1)
            observed = float(ard.read(1, window=target_window)[0, 0])
            if not ard.read_masks(1, window=target_window)[0, 0] or not math.isfinite(observed):
                raise RuntimeError("Preselected ARD diagnostic pixel is invalid")
            x, y = ard.xy(row, col)
            source_x, source_y = transform(destination_crs, source_crs, [x], [y])
            source_col, source_row = (~source_transform) * (source_x[0], source_y[0])
            first_col = math.floor(source_col) - 3
            first_row = math.floor(source_row) - 3
            if not (0 <= first_col <= width - WINDOW_SIDE and 0 <= first_row <= height - WINDOW_SIDE):
                raise RuntimeError("Diagnostic source window falls outside IMG")
            start = image_offset + first_row * record_bytes + first_col * 4
            length = (WINDOW_SIDE - 1) * record_bytes + WINDOW_SIDE * 4
            raw = reader.read(start, length)
            window_array = np.ndarray(
                (WINDOW_SIDE, WINDOW_SIDE), dtype="<f4", buffer=raw,
                strides=(record_bytes, 4),
            ).copy()
            invalid = ~np.isfinite(window_array) | (window_array == nodata)
            if invalid.any():
                raise RuntimeError("Source cubic support window contains invalid values")
            source_heights = window_array.astype("float64") * scale + offset
            output = np.full((1, 1), np.nan, dtype="float64")
            window_transform = source_transform * Affine.translation(first_col, first_row)
            reproject(
                source_heights, output, src_transform=window_transform,
                src_crs=source_crs, src_nodata=np.nan,
                dst_transform=ard.window_transform(target_window),
                dst_crs=destination_crs, dst_nodata=np.nan,
                resampling=Resampling.cubic, num_threads=1,
            )
            predicted = float(output[0, 0])
            if not math.isfinite(predicted):
                raise RuntimeError("Cubic diagnostic warp produced nodata")
            source_nearest_row = math.floor(source_row)
            source_nearest_col = math.floor(source_col)
            raw_nearest = float(window_array[source_nearest_row - first_row, source_nearest_col - first_col])
            points.append(
                {
                    "id": f"P{index}",
                    "ard_crop_row_col_zero_based": [row, col],
                    "ard_pixel_center_xy_m": [x, y],
                    "original_projected_xy_m": [source_x[0], source_y[0]],
                    "original_fractional_corner_pixel_col_row": [source_col, source_row],
                    "original_nearest_row_col_zero_based": [source_nearest_row, source_nearest_col],
                    "original_8x8_window_row_col": [first_row, first_col],
                    "original_window_sha256": hashlib.sha256(window_array.tobytes()).hexdigest(),
                    "original_window_min_max_m": [float(source_heights.min()), float(source_heights.max())],
                    "original_nearest_raw_float32": raw_nearest,
                    "nearest_source_scaled_equals_ARD_exactly": observed == raw_nearest * scale + offset,
                    "predicted_ard_cubic_m": predicted,
                    "observed_ard_float32_m": observed,
                    "observed_is_negative_and_fractional": observed < 0 and observed != math.trunc(observed),
                    "residual_observed_minus_predicted_m": observed - predicted,
                    "abs_residual_m": abs(observed - predicted),
                    "within_predeclared_tolerance": abs(observed - predicted) <= TOLERANCE_M,
                    "http_request_index": len(reader.requests) - 1,
                }
            )
        ard_metadata = {
            "path": args.ard_crop.as_posix(),
            "sha256": hashlib.sha256(args.ard_crop.read_bytes()).hexdigest(),
            "shape": [ard.height, ard.width], "dtype": ard.dtypes[0],
            "source_url": ARD_URL, "crs_wkt": destination_crs.to_wkt(),
            "transform": list(destination_transform),
        }
    passed = all(point["within_predeclared_tolerance"] for point in points)
    report = {
        "schema_version": 1, "observed_at_utc": utc_now(),
        "product_id": PRODUCT_ID,
        "passed": passed,
        "status": "pass" if passed else "diagnostic_discrepancy",
        "scope": "Three sparse original IMG to ARD numeric height-transfer diagnostics; not independent georegistration or absolute accuracy.",
        "predeclared_tolerance_m": TOLERANCE_M,
        "resampling": "cubic", "source_window_shape": [WINDOW_SIDE, WINDOW_SIDE],
        "point_selection": "Fixed crop fractions (row,col): (0.2,0.2), (0.5,0.8), (0.8,0.4); selected before source pixel reads.",
        "max_abs_residual_m": max(point["abs_residual_m"] for point in points),
        "original": {
            "url": ORIGINAL_URL, "crs_wkt_from_PDS_driver": source_crs.to_wkt(),
            "transform_from_PDS_driver": list(source_transform),
            "projection_parameters_from_label": source_params,
            "shape": [height, width], "sample_type": "PC_REAL", "sample_bits": 32,
            "record_bytes": record_bytes, "image_record_one_based": image_record,
            "image_byte_offset_zero_based": image_offset,
            "scaling_factor": scale, "offset": offset, "nodata": nodata,
            "label_prefix_sha256": hashlib.sha256(prefix).hexdigest(),
        },
        "ard_crop": ard_metadata, "points": points,
        "http": {
            "requests": reader.requests, "body_bytes_read": reader.bytes_read,
            "body_budget_bytes": BODY_BUDGET_BYTES,
            "byte_count_scope": "HTTP response bodies read by this helper only; excludes headers/TLS and prior ARD crop download.",
            "full_IMG_downloaded": False,
            "no_GDAL_remote_reads": True,
        },
        "versions": {"rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__, "numpy": np.__version__},
        "source_vertical_evidence": {
            "path": "docs/verification/T1_VERTICAL_DATUM.json",
            "sha256": hashlib.sha256(
                (Path(__file__).resolve().parent.parent / "docs/verification/T1_VERTICAL_DATUM.json").read_bytes()
            ).hexdigest(),
            "product_id": PRODUCT_ID,
        },
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limits": [
            "Sparse checks do not prove every ARD pixel equals the original.",
            "No independent terrain control, absolute accuracy, or sigma was measured.",
            "No exact areoid realization or vertical transformation model was inferred.",
            "Negative fractional sampled heights diagnose whether Float32 elevations survived; they do not reconstruct the publisher's exact command history.",
        ],
    }
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
