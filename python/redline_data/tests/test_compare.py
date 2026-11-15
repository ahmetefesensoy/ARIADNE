"""Small synthetic product bundles; no NASA measurements are invented."""
import hashlib
import json
import math

import pytest

np = pytest.importorskip("numpy")
rasterio = pytest.importorskip("rasterio")
pyproj = pytest.importorskip("pyproj")
from rasterio.transform import from_origin

from redline_data.compare import compare_dems


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rewrite(path, metadata):
    path.write_text(json.dumps(metadata), encoding="utf-8")


@pytest.fixture
def bundle(tmp_path):
    paths = []
    evidence_products = {}
    wkt = pyproj.CRS.from_proj4("+proj=eqc +R=3396190 +units=m +type=crs").to_wkt()
    for label, shift_x, shift_y, bias in (("primary", 3.2, -2.3, 6), ("reference", 0, 0, 0)):
        raw = tmp_path / f"raw_{label}.tif"
        raw.write_bytes(f"synthetic fixture {label}".encode())
        product_id, source_url = f"synthetic-{label}", f"https://example.invalid/{label}.tif"
        rewrite(raw.with_suffix(".provenance.json"), {"sha256": digest(raw),
            "identity": {"product_id": product_id, "source": source_url}})
        declaration = tmp_path / f"{label}-declaration.txt"
        declaration.write_text(f"Synthetic test only: {label} declared metric vertical context")
        evidence_products[product_id] = {"product_id": product_id, "source_url": source_url,
            "units": "m", "target": "Mars", "vertical_datum": f"Synthetic {label} datum declaration",
            "declaration_status": "metadata_verified_synthetic_fixture",
            "ard_transfer_status": "not independently verified synthetic fixture",
            "evidence": [{"path": declaration.name, "sha256": digest(declaration),
                          "size_bytes": declaration.stat().st_size}]}
        for resolution in (1, 4):
            count = 160 // resolution
            transform = from_origin(23, 90, resolution, resolution)
            rows, cols = np.indices((count, count))
            xx = 23 + (cols+.5)*resolution - shift_x
            yy = 90 - (rows+.5)*resolution - shift_y
            values = -4200 + 5*np.sin(xx/14) + 3*np.cos(yy/19) + 2*np.sin((xx+yy)/21) + bias
            path = tmp_path / f"{label}_{resolution}m.tif"
            with rasterio.open(path, "w", driver="GTiff", width=count, height=count,
                               count=1, dtype="float32", nodata=np.nan, transform=transform) as dst:
                dst.write(values.astype("float32"), 1)
            metadata = {"sha256": digest(path), "status": "DERIVED", "frame": "map", "units": "m",
                "source": str(raw), "source_wkt": wkt, "resolution_m": resolution,
                "origin": {"E0_m": 0, "N0_m": 0, "H0_m": 0, "status": "SCENARIO"},
                "east_scale_factor": 1, "shape": [count, count], "transform": list(transform),
                "identity": {"kind": "dem", "source_sha256": digest(raw), "resolution_m": resolution,
                    "center_lat": 0, "center_lon_east": 0, "h0_m": 0, "size_m": [160,160],
                    "expected": {"sphere_radius_m": 3396190, "lon_0_deg": 0, "lat_ts_deg": 0}}}
            rewrite(path.with_suffix(".provenance.json"), metadata)
            paths.append(path)
    evidence = tmp_path / "vertical.json"
    rewrite(evidence, {"products": evidence_products})
    return [paths[0], paths[2], paths[1], paths[3]], evidence


def run(bundle, destination, **kwargs):
    paths, evidence = bundle
    return compare_dems(*paths, destination=destination, vertical_evidence=evidence, **kwargs)


def test_persisted_comparison_has_degree_proxy_and_complete_individual_sidecars(bundle, tmp_path):
    destination = tmp_path / "comparison"
    result = run(bundle, destination)
    assert result["registration"]["shift_east_m"] == pytest.approx(3.2, abs=.2)
    assert result["registration"]["shift_north_m"] == pytest.approx(-2.3, abs=.2)
    assert result["registration"]["vertical_offset_removed_m"] == pytest.approx(6, abs=.1)
    assert result["after_shared"]["rmse_m"] < result["before_shared"]["rmse_m"]
    assert not result["milestone_T1_complete"]
    assert len(result["assets"]) == 3
    primary_meta = json.loads(bundle[0][0].with_suffix(".provenance.json").read_text())
    for name, record in result["assets"].items():
        path = destination / record["href"]
        sidecar = destination / record["metadata"]
        metadata = json.loads(sidecar.read_text())
        assert digest(path) == record["sha256"] == metadata["sha256"]
        assert digest(sidecar) == record["metadata_sha256"]
        for key in ("source_wkt", "origin", "east_scale_factor", "shape", "transform"):
            assert metadata[key] == primary_meta[key]
        assert metadata["relative_registration_accepted"]
        assert not metadata["alignment_verified"]
        with rasterio.open(path) as src:
            assert src.crs is None and src.dtypes == ("float32",)
            assert list(src.transform) == primary_meta["transform"]
            assert math.isnan(src.nodata)
            assert np.isfinite(src.read(1)).any()
    assert result["assets"]["slope_sigma"]["unit"] == "degree"
    assert result["slope_disagreement"]["baseline_m"] == 5
    assert "NOT independent one-sigma" in result["slope_disagreement"]["interpretation"]
    assert result["vertical_evidence"]["products"]["synthetic-reference"]["ard_transfer_status"] == "not independently verified synthetic fixture"
    assert run(bundle, destination) == result


@pytest.mark.parametrize("alter", ["raster", "sidecar", "evidence", "extra"])
def test_cache_never_accepts_tampered_artifacts_or_changed_evidence(bundle, tmp_path, alter):
    destination = tmp_path / "comparison"
    result = run(bundle, destination)
    if alter == "raster":
        (destination/result["assets"]["slope_sigma"]["href"]).write_bytes(b"tampered")
    elif alter == "sidecar":
        (destination/result["assets"]["slope_sigma"]["metadata"]).write_text("{}")
    elif alter == "evidence":
        bundle[1].write_text("different evidence")
    else:
        (destination/"unexpected.txt").write_text("incomplete other run")
    with pytest.raises(ValueError):
        run(bundle, destination)


@pytest.mark.parametrize("field,value", [("units", "degree"), ("shape", [1,1]),
    ("origin", {"E0_m": 1,"N0_m":0,"H0_m":0}), ("east_scale_factor", .5)])
def test_source_sidecar_must_describe_actual_metric_grid(bundle, tmp_path, field, value):
    source = bundle[0][1]
    sidecar = source.with_suffix(".provenance.json")
    metadata = json.loads(sidecar.read_text())
    metadata[field] = value
    rewrite(sidecar, metadata)
    with pytest.raises(ValueError):
        run(bundle, tmp_path/"out")
    assert not (tmp_path/"out").exists()


def test_changed_input_raster_and_partial_cache_are_rejected(bundle, tmp_path):
    destination = tmp_path/"out"
    destination.mkdir()
    (destination/"aligned_reference.tif").write_bytes(b"partial")
    with pytest.raises(ValueError, match="Incomplete"):
        run(bundle, destination)
    bundle[0][0].write_bytes(b"modified")
    with pytest.raises(ValueError, match="hash"):
        run(bundle, tmp_path/"other")


def test_fit_resolution_must_share_same_product_and_grid_mapping(bundle, tmp_path):
    path = bundle[0][2].with_suffix(".provenance.json")
    metadata = json.loads(path.read_text())
    metadata["identity"]["center_lat"] = 1
    rewrite(path, metadata)
    with pytest.raises(ValueError):
        run(bundle, tmp_path/"out")


def test_missing_or_empty_vertical_evidence_is_not_accepted(bundle, tmp_path):
    bundle[1].write_text("")
    with pytest.raises(ValueError):
        run(bundle, tmp_path/"out")


@pytest.mark.parametrize("fault", ["wrong_product", "missing_units", "wrong_url", "corrupt_artifact"])
def test_evidence_requires_exact_products_units_urls_and_source_hashes(bundle, tmp_path, fault):
    path = bundle[1]
    record = json.loads(path.read_text())
    if fault == "wrong_product":
        record["products"]["other"] = record["products"].pop("synthetic-primary")
    elif fault == "missing_units":
        del record["products"]["synthetic-primary"]["units"]
    elif fault == "wrong_url":
        record["products"]["synthetic-primary"]["source_url"] = "https://example.invalid/wrong"
    else:
        (path.parent/record["products"]["synthetic-primary"]["evidence"][0]["path"]).write_text("tampered")
    rewrite(path, record)
    with pytest.raises(ValueError):
        run(bundle, tmp_path/"out")
    assert not (tmp_path/"out").exists()
