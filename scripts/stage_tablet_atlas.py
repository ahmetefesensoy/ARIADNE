"""Validate the BXW tablet atlas, then copy its original bytes to UE Content.

The manifest declares a local map in metres, not a planetary CRS. This helper
does not reinterpret it or regenerate layers. Every input is checked before
creating or changing a destination. I/O failures during copying are reported;
the operation is not a transaction across separate destination directories.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import tempfile
import zlib

LAYERS = ("imagery", "hillshade", "slope_class", "science_units", "return_time", "stations")
COMPOSITES = ("composite.png", "composite_safety.png", "composite_science.png")
MAX_PNG_BYTES = 16 * 1024 * 1024
SIZE_PX = 2048


def _reject_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate manifest key: " + key)
        result[key] = value
    return result


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _check_numbers(value, depth=0):
    if depth > 32:
        raise ValueError("manifest nesting exceeds bound")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("manifest contains a nonfinite number")
    if isinstance(value, dict):
        for item in value.values():
            _check_numbers(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check_numbers(item, depth + 1)


def _bounded_read(path, limit):
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"missing or oversized input: {path.name}")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"oversized input: {path.name}")
    return data


def _png_name(value):
    if (not isinstance(value, str) or not value or len(value) > 128
            or value in (".", "..") or any(c in value for c in "/\\:\x00")
            or not value.endswith(".png")):
        raise ValueError("layer file must be a PNG basename without traversal")
    return value


def _validate_png(data, name):
    if len(data) < 45 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"invalid PNG header: {name}")
    length, kind = struct.unpack(">I4s", data[8:16])
    if length != 13 or kind != b"IHDR":
        raise ValueError(f"invalid PNG IHDR: {name}")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", data[16:29])
    if zlib.crc32(data[12:29]) & 0xFFFFFFFF != struct.unpack(">I", data[29:33])[0]:
        raise ValueError(f"invalid PNG IHDR CRC: {name}")
    depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
    if ((width, height) != (SIZE_PX, SIZE_PX) or depth not in depths.get(color, ())
            or compression != 0 or filtering != 0 or interlace not in (0, 1)):
        raise ValueError(f"PNG must declare supported {SIZE_PX} x {SIZE_PX} pixels: {name}")
    # Header validation is deliberately not a substitute for image decoding.
    if data[-12:] != b"\x00\x00\x00\x00IEND\xaeB`\x82":
        raise ValueError(f"PNG IEND missing: {name}")


def validate_source(source):
    """Return checked manifest, original file bytes and receipt entries."""
    source = Path(source).resolve()
    raw = _bounded_read(source / "manifest.json", 1024 * 1024)
    try:
        manifest = json.loads(raw, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("invalid atlas manifest JSON") from error
    if not isinstance(manifest, dict):
        raise ValueError("atlas manifest must be an object")
    _check_numbers(manifest)
    if (manifest.get("schema") != "redline.tablet_atlas.v1" or manifest.get("site_id") != "BXW"
            or manifest.get("frame") != "map" or manifest.get("units") != "m"
            or manifest.get("north_up") is not True):
        raise ValueError("atlas schema/site/frame/units/north_up contract mismatch")
    bounds = manifest.get("bounds_map_m")
    if not isinstance(bounds, list) or len(bounds) != 4 or not all(_finite(v) for v in bounds):
        raise ValueError("atlas bounds must be four finite numbers")
    xmin, ymin, xmax, ymax = bounds
    if xmin >= xmax or ymin >= ymax:
        raise ValueError("atlas bounds must increase")
    scale = manifest.get("m_per_px")
    if (type(manifest.get("size_px")) is not int or manifest["size_px"] != SIZE_PX
            or not _finite(scale) or scale <= 0
            or not all(math.isclose(span / SIZE_PX, scale, rel_tol=1e-9, abs_tol=1e-9)
                       for span in (xmax - xmin, ymax - ymin))):
        raise ValueError("atlas size/m_per_px does not match its bounds")
    stations = manifest.get("stations")
    if not isinstance(stations, list) or len(stations) > 32:
        raise ValueError("atlas stations must be an array of at most 32 records")
    ids = set()
    for station in stations:
        if not isinstance(station, dict):
            raise ValueError("invalid station record")
        ident, xy = station.get("id"), station.get("xy_m")
        if (not isinstance(ident, str) or not 1 <= len(ident.encode("utf-8")) <= 128 or ident in ids
                or not isinstance(xy, list) or len(xy) != 2 or not all(_finite(v) for v in xy)
                or not xmin <= xy[0] <= xmax or not ymin <= xy[1] <= ymax
                or ("z_m" in station and not _finite(station["z_m"]))):
            raise ValueError("station ID/finite in-bounds position contract mismatch")
        ids.add(ident)
    layers = manifest.get("layers")
    if not isinstance(layers, dict) or set(layers) != set(LAYERS):
        raise ValueError("atlas requires exactly the six allowlisted layers")
    files = {"manifest.json": raw}
    records = [{"file": "manifest.json", "kind": "manifest", "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()}]
    for layer in LAYERS:
        entry = layers[layer]
        if not isinstance(entry, dict):
            raise ValueError("invalid layer record: " + layer)
        name = _png_name(entry.get("file"))
        if name in files or name in COMPOSITES:
            raise ValueError("duplicate or reserved atlas filename: " + name)
        expected = entry.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("invalid layer SHA-256: " + layer)
        path = source / name
        if path.resolve().parent != source:
            raise ValueError("layer path escapes atlas source")
        data = _bounded_read(path, MAX_PNG_BYTES)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("layer SHA-256 mismatch: " + layer)
        _validate_png(data, name)
        files[name] = data
        records.append({"file": name, "layer": layer, "kind": "layer", "bytes": len(data), "sha256": expected})
    for name in COMPOSITES:
        path = source / name
        if not path.exists():
            continue
        if path.resolve().parent != source:
            raise ValueError("composite path escapes atlas source")
        data = _bounded_read(path, MAX_PNG_BYTES)
        _validate_png(data, name)
        files[name] = data
        records.append({"file": name, "kind": "composite", "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()})
    return manifest, files, records


def _atomic_write(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".atlas-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def stage(source, destinations, report=None):
    source = Path(source).resolve()
    manifest, files, records = validate_source(source)
    destinations = [Path(path).resolve() for path in destinations]
    if not destinations or len(set(destinations)) != len(destinations):
        raise ValueError("one or more distinct destinations are required")
    for dest in destinations:
        if dest == source or dest in source.parents or source in dest.parents:
            raise ValueError("destination must be separate from original atlas source")
        if dest.exists() and not dest.is_dir():
            raise ValueError("destination is not a directory")
        if any(parent.exists() and not parent.is_dir() for parent in dest.parents):
            raise ValueError("destination ancestor is not a directory")
        if any((dest / name).exists() and not (dest / name).is_file() for name in files):
            raise ValueError("destination contains a non-file atlas entry")
    report = Path(report).resolve() if report is not None else None
    if report is not None and (report == source or source in report.parents
                               or any(report == dest / name for dest in destinations for name in files)
                               or any(report == dest or report in dest.parents for dest in destinations)
                               or (report.exists() and not report.is_file())):
        raise ValueError("report path would replace an atlas input/output or directory")
    if report is not None and any(parent.exists() and not parent.is_dir() for parent in report.parents):
        raise ValueError("report ancestor is not a directory")
    receipt = {"schema": "redline.tablet_atlas.stage.v1", "passed": True,
               "generated_utc": datetime.now(timezone.utc).isoformat(), "source": str(source),
               "site_id": manifest["site_id"], "frame": manifest["frame"],
               "manifest_sha256": records[0]["sha256"], "files": records,
               "destinations": [str(dest) for dest in destinations],
               "validation": "manifest contracts, SHA-256 and PNG header/IEND; no pixel decoding or CRS inference"}
    # All source and path checks above finish before the first mutation.
    for dest in destinations:
        dest.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            _atomic_write(dest / name, data)
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(report, (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return receipt


def main():
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=repo / "data/engines/BXW/tablet-atlas-v1")
    parser.add_argument("--destination", type=Path, action="append", help="Repeat to stage both UE content roots")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    destinations = args.destination
    if destinations is None:
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            parser.error("pass --destination for each UE Content/Atlas root outside Windows")
        destinations = [repo / "unreal/Redline/Content/Atlas", Path(local) / "Redline/T4Build/Redline/Content/Atlas"]
    print(json.dumps(stage(args.source, destinations, args.report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
