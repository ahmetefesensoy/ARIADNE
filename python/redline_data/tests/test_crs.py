import pytest

pyproj = pytest.importorskip("pyproj", reason="install redline-data[data] for GIS tests")
from redline_data.crs import ExpectedCrs, check_wkt

EXPECTED = ExpectedCrs(3396190.0, 0, 0)


def mars_wkt(**options):
    params = dict(proj="eqc", R=3396190, lon_0=0, lat_ts=0, units="m")
    params.update(options)
    return pyproj.CRS.from_dict(params).to_wkt()


def test_accepts_explicit_product_mars_sphere_and_reports_limits():
    report = check_wkt(mars_wkt(), EXPECTED)
    assert report["sphere_radius_m"] == 3396190
    assert not report["alignment_verified"]
    assert "not established" in report["vertical_reference"]


@pytest.mark.parametrize("wkt", [None, "", pyproj.CRS.from_epsg(4326).to_wkt(), pyproj.CRS.from_epsg(3857).to_wkt()])
def test_no_earth_or_missing_crs_fallback(wkt):
    with pytest.raises(ValueError):
        check_wkt(wkt, EXPECTED)


@pytest.mark.parametrize("options", [{"R": 3396160}, {"lon_0": 137}, {"lat_ts": -4.8}, {"x_0": 100}, {"proj": "merc"}, {"units": "km"}])
def test_source_parameters_cannot_be_relabelled(options):
    with pytest.raises(ValueError):
        check_wkt(mars_wkt(**options), EXPECTED)


def test_nonspherical_mars_ellipsoid_is_not_silently_accepted():
    wkt = pyproj.CRS.from_proj4("+proj=eqc +a=3396190 +b=3376200 +units=m").to_wkt()
    with pytest.raises(ValueError, match="spherical"):
        check_wkt(wkt, EXPECTED)


@pytest.mark.parametrize("radius", [6378137, float("nan"), 0])
def test_configuration_is_explicitly_mars(radius):
    with pytest.raises(ValueError):
        ExpectedCrs(radius, 0, 0)


@pytest.mark.parametrize('options', [{'y_0': 100}, {'lat_0': 1}])
def test_additional_source_origin_offsets_are_not_silently_accepted(options):
    with pytest.raises(ValueError):
        check_wkt(mars_wkt(**options), EXPECTED)


def test_projection_wkt_with_swapped_axes_is_rejected():
    swapped = pyproj.CRS.from_proj4('+proj=eqc +R=3396190 +units=m +axis=neu').to_wkt()
    with pytest.raises(ValueError, match='axis order'):
        check_wkt(swapped, EXPECTED)


@pytest.mark.parametrize('wkt', ['not-WKT', 'PROJCRS[', 'EPSG:4326'])
def test_malformed_or_non_wkt_inputs_do_not_get_relabelled(wkt):
    with pytest.raises(ValueError):
        check_wkt(wkt, EXPECTED)
