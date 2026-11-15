"""Atlas staging preserves bytes and rejects misleading map/image contracts."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("stage_tablet_atlas", ROOT / "scripts/stage_tablet_atlas.py")
atlas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atlas)


def png(width=2048, height=2048, value=0):
    """A complete valid grayscale PNG, not merely a fabricated dimension header."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    scan = (b"\0" + bytes([value]) * width) * height
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scan)) + chunk(b"IEND", b""))


@pytest.fixture
def source(tmp_path):
    directory = tmp_path / "original"
    directory.mkdir()
    image = png()
    manifest = {"schema": "redline.tablet_atlas.v1", "site_id": "BXW", "frame": "map", "units": "m",
                "north_up": True, "bounds_map_m": [-1500., -1500., 1500., 1500.],
                "size_px": 2048, "m_per_px": 3000 / 2048, "note": "Özgün kaynak korunur",
                "stations": [{"id": "ST-H", "xy_m": [290., -454.], "z_m": -3581.61}],
                "layers": {layer: {"file": layer + ".png", "sha256": hashlib.sha256(image).hexdigest(),
                                    "status": "SCENARIO"} for layer in atlas.LAYERS}}
    for layer in atlas.LAYERS:
        (directory / (layer + ".png")).write_bytes(image)
    write_manifest(directory, manifest)
    return directory, manifest


def write_manifest(directory, manifest):
    (directory / "manifest.json").write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def test_roundtrip_two_destinations_is_byte_exact_and_receipts_optional_composite(source, tmp_path):
    directory, _ = source
    (directory / "composite_science.png").write_bytes(png(value=15))
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    destinations = [tmp_path / "repo/Content/Atlas", tmp_path / "ascii-cache/Content/Atlas"]
    report = tmp_path / "proof/stage.json"
    receipt = atlas.stage(directory, destinations, report)
    assert receipt["passed"] and receipt["frame"] == "map"
    assert json.loads(report.read_bytes()) == receipt
    assert {entry["kind"] for entry in receipt["files"]} == {"manifest", "layer", "composite"}
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before
    for dest in destinations:
        assert {path.name: path.read_bytes() for path in dest.iterdir()} == before
    for entry in receipt["files"]:
        assert entry["sha256"] == hashlib.sha256(before[entry["file"]]).hexdigest()
        assert entry["bytes"] == len(before[entry["file"]])


@pytest.mark.parametrize("field,value", [
    ("schema", "redline.tablet_atlas.v2"), ("site_id", "YKB"), ("frame", "EPSG:4326"),
    ("units", "cm"), ("north_up", False), ("north_up", 1), ("size_px", 1024),
    ("m_per_px", 1.), ("bounds_map_m", [-1500, -1500, 1500, 1400]),
    ("bounds_map_m", [float("nan"), -1500, 1500, 1500]),
])
def test_wrong_map_crs_orientation_or_scale_fails_before_mutation(source, tmp_path, field, value):
    directory, manifest = source
    manifest[field] = value
    write_manifest(directory, manifest)
    dest = tmp_path / "not-created/Atlas"
    report = tmp_path / "not-created/report.json"
    with pytest.raises(ValueError):
        atlas.stage(directory, [dest], report)
    assert not dest.parent.exists() and not report.exists()


@pytest.mark.parametrize("filename", ["../outside.png", "sub/file.png", "..\\outside.png", "C:outside.png"])
def test_layer_path_traversal_rejected_before_any_destination_changes(source, tmp_path, filename):
    directory, manifest = source
    manifest["layers"]["imagery"]["file"] = filename
    write_manifest(directory, manifest)
    existing = tmp_path / "existing"
    existing.mkdir()
    sentinel = existing / "manifest.json"
    sentinel.write_bytes(b"previous accepted atlas")
    other = tmp_path / "other"
    with pytest.raises(ValueError, match="basename"):
        atlas.stage(directory, [existing, other])
    assert sentinel.read_bytes() == b"previous accepted atlas" and not other.exists()


def test_sha_mismatch_rejected_before_changing_existing_manifest(source, tmp_path):
    directory, manifest = source
    manifest["layers"]["imagery"]["sha256"] = "0" * 64
    write_manifest(directory, manifest)
    dest = tmp_path / "destination"
    dest.mkdir()
    sentinel = dest / "manifest.json"
    sentinel.write_bytes(b"existing")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        atlas.stage(directory, [dest])
    assert sentinel.read_bytes() == b"existing" and list(dest.iterdir()) == [sentinel]


@pytest.mark.parametrize("image", [b"not a PNG", png(1024, 2048), png()[:-12]])
def test_png_header_dimensions_and_truncation_are_checked_after_hash(source, tmp_path, image):
    directory, manifest = source
    (directory / "hillshade.png").write_bytes(image)
    manifest["layers"]["hillshade"]["sha256"] = hashlib.sha256(image).hexdigest()
    write_manifest(directory, manifest)
    with pytest.raises(ValueError, match="PNG"):
        atlas.stage(directory, [tmp_path / "destination"])
    assert not (tmp_path / "destination").exists()


@pytest.mark.parametrize("stations", [
    [{"id": "outside", "xy_m": [1500.1, 0]}], [{"id": "bad", "xy_m": [0, float("inf")]}],
    [{"id": "bad", "xy_m": [True, 0]}], [{"id": "bad", "xy_m": [0, 0], "z_m": "unknown"}],
    [{"id": "same", "xy_m": [0, 0]}] * 2,
    [{"id": f"station-{i}", "xy_m": [0, 0]} for i in range(33)],
])
def test_invalid_or_unbounded_stations_rejected(source, tmp_path, stations):
    directory, manifest = source
    manifest["stations"] = stations
    write_manifest(directory, manifest)
    with pytest.raises(ValueError):
        atlas.stage(directory, [tmp_path / "destination"])
    assert not (tmp_path / "destination").exists()


def test_missing_or_extra_layers_cannot_silently_change_allowlist(source, tmp_path):
    directory, manifest = source
    manifest["layers"]["unreviewed"] = manifest["layers"].pop("stations")
    write_manifest(directory, manifest)
    with pytest.raises(ValueError, match="six allowlisted"):
        atlas.stage(directory, [tmp_path / "destination"])


def test_oversized_png_rejected_without_reading_it_into_staging(source, tmp_path):
    directory, _ = source
    with (directory / "stations.png").open("r+b") as stream:
        stream.truncate(atlas.MAX_PNG_BYTES + 1)
    with pytest.raises(ValueError, match="oversized"):
        atlas.stage(directory, [tmp_path / "destination"])
    assert not (tmp_path / "destination").exists()


def test_all_destinations_are_checked_before_first_copy(source, tmp_path):
    directory, _ = source
    invalid = tmp_path / "file-not-directory"
    invalid.write_bytes(b"unrelated")
    first = tmp_path / "first"
    with pytest.raises(ValueError, match="directory"):
        atlas.stage(directory, [first, invalid])
    assert not first.exists() and invalid.read_bytes() == b"unrelated"


def test_original_source_cannot_be_used_as_destination_or_report(source):
    directory, _ = source
    before = (directory / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="separate"):
        atlas.stage(directory, [directory])
    with pytest.raises(ValueError, match="report path"):
        atlas.stage(directory, [directory.parent / "dest"], directory / "manifest.json")
    assert (directory / "manifest.json").read_bytes() == before


def test_report_cannot_collide_with_destination_directory(source, tmp_path):
    directory, _ = source
    dest = tmp_path / "new-destination"
    with pytest.raises(ValueError, match="report path"):
        atlas.stage(directory, [dest], dest)
    assert not dest.exists()


def test_invalid_destination_or_report_ancestor_fails_before_mutation(source, tmp_path):
    directory, _ = source
    blocked = tmp_path / "regular-file"
    blocked.write_bytes(b"unrelated")
    first = tmp_path / "first"
    with pytest.raises(ValueError, match="ancestor"):
        atlas.stage(directory, [first, blocked / "Atlas"])
    assert not first.exists()
    with pytest.raises(ValueError, match="ancestor"):
        atlas.stage(directory, [first], blocked / "receipt.json")
    assert not first.exists() and blocked.read_bytes() == b"unrelated"
