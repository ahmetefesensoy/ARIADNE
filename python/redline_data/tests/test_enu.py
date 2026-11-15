"""Analytical synthetic fixtures; no NASA measurement values invented."""
import math

import pytest

np = pytest.importorskip("numpy")
rasterio = pytest.importorskip("rasterio")
pytest.importorskip("pyproj")
from rasterio.transform import from_origin

from redline_data.crs import ExpectedCrs
from redline_data.enu import to_local

EXPECTED = ExpectedCrs(3396190, 0, 0)


@pytest.fixture
def source(tmp_path):
    # At 60 degrees, x = E/2. This makes a missing cosine correction obvious.
    n0 = 3396190 * math.radians(60)
    transform = from_origin(-50, n0 + 50, 1, 1)
    rows, cols = np.indices((100, 100))
    east = -50 + cols + .5
    north = 50 - rows - .5
    data = (100 + .4 * east + .3 * north).astype("float32")
    path = tmp_path / "source.tif"
    with rasterio.open(path, "w", driver="GTiff", width=100, height=100, count=1,
                       dtype="float32", nodata=np.nan, transform=transform,
                       crs="+proj=eqc +R=3396190 +lon_0=0 +lat_ts=0 +units=m +type=crs") as dst:
        dst.write(data, 1)
    return path


def convert(source, tmp_path, **overrides):
    args = dict(center_lat=60, center_lon_east=0, h0_m=100,
                resolution_m=1, size_m=(20, 20), destination=tmp_path / "local.tif",
                expected=EXPECTED)
    args.update(overrides)
    return to_local(source, **args)


def test_local_centres_have_correct_cosine_north_sign_and_vertical_offset(source, tmp_path):
    result = convert(source, tmp_path)
    with rasterio.open(tmp_path / "local.tif") as local:
        assert local.crs is None  # no geographic label on engineering metres
        values = local.read(1)
        for row, col in ((2, 3), (10, 10), (17, 16)):
            x, y = local.xy(row, col)
            # Independent analytical surface: E=2*x and N-N0=y.
            assert values[row, col] == pytest.approx(.8*x + .3*y, abs=1e-5)
    assert result["east_scale_factor"] == pytest.approx(.5)
    assert result["origin"]["H0_m"] == 100
    assert result["alignment_verified"] is False
    assert "Mars" in result["source_wkt"] or "3396190" in result["source_wkt"]


def test_unknown_source_support_is_not_filled_across_hole(source, tmp_path):
    with rasterio.open(source, "r+") as src:
        values = src.read(1)
        values[49:52, 49:52] = np.nan
        src.write(values, 1)
    report = convert(source, tmp_path)
    with rasterio.open(tmp_path / "local.tif") as dst:
        assert np.isnan(dst.read(1)[9:11, 9:11]).all()
    assert 0 < report["nodata_fraction"] < .1


def test_class_resampling_never_interpolates_labels(source, tmp_path):
    with rasterio.open(source, "r+") as src:
        src.write((np.indices((100, 100))[1] % 2 * 7).astype("float32"), 1)
    convert(source, tmp_path, kind="class", h0_m=0)
    with rasterio.open(tmp_path / "local.tif") as dst:
        assert set(np.unique(dst.read(1))) <= {0, 7}


def test_hash_verified_cache_refuses_changed_source_and_output(source, tmp_path):
    first = convert(source, tmp_path)
    assert convert(source, tmp_path) == first
    with rasterio.open(source, "r+") as src:
        values = src.read(1)
        values[0, 0] += 10
        src.write(values, 1)
    with pytest.raises(ValueError, match="request/hash"):
        convert(source, tmp_path)


@pytest.mark.parametrize("overrides", [dict(resolution_m=0), dict(size_m=(21,20), resolution_m=2),
    dict(size_m=(1000,1000)), dict(max_pixels=3), dict(center_lat=90),
    dict(h0_m=float("nan")), dict(kind="other")])
def test_invalid_or_uncovered_local_requests_write_nothing(source, tmp_path, overrides):
    with pytest.raises(ValueError):
        convert(source, tmp_path, **overrides)
    assert not (tmp_path / "local.tif").exists()


def test_source_crs_must_match_product_expectation(source, tmp_path):
    with rasterio.open(source, "r+") as src:
        src.crs = "EPSG:3857"
    with pytest.raises(ValueError):
        convert(source, tmp_path)
