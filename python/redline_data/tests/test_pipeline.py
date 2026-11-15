"""Offline source→ENU→terrain→QA integration with known metric geometry."""
import json
import math

import pytest

np = pytest.importorskip("numpy")
rasterio = pytest.importorskip("rasterio")
pytest.importorskip("pyproj")
from rasterio.transform import from_origin
from redline_data.crs import ExpectedCrs
from redline_data.derive import write_products
from redline_data.enu import to_local
from redline_data.qa import report, three_points


@pytest.fixture
def products(tmp_path):
    source = tmp_path / "source.tif"
    rows, cols = np.indices((100, 100))
    values = 50 + .4*(-50+cols+.5) + .3*(50-rows-.5)
    with rasterio.open(source, "w", driver="GTiff", count=1, height=100, width=100,
                       dtype="float32", nodata=np.nan, transform=from_origin(-50, 3396190*math.radians(60)+50,1,1),
                       crs="+proj=eqc +R=3396190 +units=m +type=crs") as dst:
        dst.write(values.astype("float32"), 1)
    local = tmp_path / "local.tif"
    to_local(source, center_lat=60, center_lon_east=0, h0_m=50,
             resolution_m=1, destination=local, expected=ExpectedCrs(3396190,0,0), size_m=(20,20))
    return source, local


def test_full_numerical_pipeline_keeps_unknown_sigma_and_real_pngs(products, tmp_path):
    source, local = products
    terrain = tmp_path / "terrain"
    derivatives = write_products(local, terrain)
    assert write_products(local, terrain) == derivatives
    assert derivatives["sigma"]["available"] is False
    assert not (terrain / "slope_sigma.tif").exists()
    expected_slope = math.degrees(math.atan(math.hypot(.8,.3)))
    with rasterio.open(terrain / "slope_5m.tif") as src:
        np.testing.assert_allclose(src.read(1)[3:-3,3:-3], expected_slope, atol=1e-4)
    qa_dir = tmp_path / "qa"
    result = report(source, local, terrain=terrain, destination=qa_dir)
    assert result["numerical_checks_passed"]
    assert not result["milestone_T1_complete"]
    assert len(result["three_points"]) == 3
    assert max(p["absolute_error_m"] for p in result["three_points"]) < 1e-5
    for key in ("dem_preview", "slope_2m_preview", "slope_5m_preview"):
        path = qa_dir/result["artifacts"][key]["href"]
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        with rasterio.open(path) as image:
            assert image.count == 3
    assert report(source, local, terrain=terrain, destination=qa_dir) == result
    html = (qa_dir / "qa.html").read_text()
    assert "T1 complete: false" in html and "vertical datum" in html


def test_qa_and_derivatives_refuse_tampered_local_terrain(products, tmp_path):
    source, local = products
    with rasterio.open(local, "r+") as src:
        values = src.read(1)
        values[10,10] += 3
        src.write(values, 1)
    with pytest.raises(ValueError, match="hash"):
        three_points(source, local)
    with pytest.raises(ValueError, match="provenance"):
        write_products(local, tmp_path/"terrain")


def test_missing_source_is_not_accepted_as_qa_ground_truth(products, tmp_path):
    _source, local = products
    with pytest.raises(FileNotFoundError):
        three_points(tmp_path/"missing.tif", local)


def test_derivative_cache_verifies_output_hash(products, tmp_path):
    _source, local = products
    target = tmp_path/"terrain"
    write_products(local, target)
    (target/"slope_2m.tif").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash"):
        write_products(local, target)
