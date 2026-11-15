from pathlib import Path
import json
import math
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen as real_urlopen

import pytest

np = pytest.importorskip("numpy", reason="install redline-data[data] for GIS tests")
rasterio = pytest.importorskip("rasterio", reason="install redline-data[data] for GIS tests")
from pyproj import CRS
from rasterio.transform import from_origin
from redline_data.crs import ExpectedCrs
from redline_data.fetch import WindowRequest, extract_window, site_bounds
from redline_data import fetch

EXPECTED = ExpectedCrs(3396190, 0, 0)


@pytest.fixture
def fixture_dem(tmp_path):
    path = tmp_path / "synthetic.tif"
    crs = CRS.from_proj4("+proj=eqc +R=3396190 +units=m")
    center_n = 3396190 * math.radians(-4.805)
    center_e = 3396190 * math.radians(137.370)
    values = np.arange(10000, dtype="float32").reshape(100, 100)
    values[50, 50] = -32767
    with rasterio.open(path, "w", driver="GTiff", height=100, width=100, count=1,
                       dtype="float32", crs=crs, nodata=-32767,
                       transform=from_origin(center_e-50, center_n+50, 1, 1)) as dst:
        dst.write(values, 1)
    return path, values


def request(size=(20.0, 20.0)):
    return WindowRequest("BXW", -4.805, 137.370, size)


def test_window_pixels_mask_and_center_registration_match_source(fixture_dem, tmp_path):
    source, values = fixture_dem
    output = tmp_path / "crop.tif"
    result = extract_window(str(source), request(), EXPECTED, output, product_id="synthetic-test-dem")
    col, row, width, height = result["source_window"]
    assert (width, height) == (22, 20)  # cos(phi0) changes east-west source width.
    assert result["status"] == "DERIVED"
    with rasterio.open(output) as crop, rasterio.open(source) as src:
        actual = crop.read(1, masked=True)
        expected = src.read(1, window=((row, row+height), (col, col+width)), masked=True)
        np.testing.assert_array_equal(actual.mask, expected.mask)
        np.testing.assert_array_equal(actual.compressed(), expected.compressed())
        # Three interior pixel centres: independent source samples and world
        # coordinates, preserving PixelIsArea/Point interpretation in GDAL.
        for y, x in [(2, 3), (height//2, width//3), (height-3, width-4)]:
            assert crop.xy(y, x) == pytest.approx(src.xy(row+y, col+x), abs=1e-8)
            assert actual[y, x] == values[row+y, col+x]
    assert result["nodata_fraction"] > 0
    assert json.loads(output.with_suffix(".provenance.json").read_text())["sha256"] == result["sha256"]


def test_exact_repeated_request_reuses_verified_artifact(fixture_dem, tmp_path):
    source, _ = fixture_dem
    output = tmp_path / "crop.tif"
    first = extract_window(str(source), request(), EXPECTED, output, product_id="synthetic-test-dem")
    stamp = output.stat().st_mtime_ns
    assert extract_window(str(source), request(), EXPECTED, output, product_id="synthetic-test-dem") == first
    assert output.stat().st_mtime_ns == stamp
    with pytest.raises(ValueError, match="differs"):
        extract_window(str(source), request((10, 10)), EXPECTED, output, product_id="synthetic-test-dem")


def test_corrupted_artifact_is_rejected(fixture_dem, tmp_path):
    source, _ = fixture_dem
    output = tmp_path / "crop.tif"
    extract_window(str(source), request(), EXPECTED, output, product_id="synthetic-test-dem")
    output.write_bytes(b"tampered-test-fixture")
    with pytest.raises(ValueError, match="differs"):
        extract_window(str(source), request(), EXPECTED, output, product_id="synthetic-test-dem")


@pytest.mark.parametrize("size,limit,block_limit,match", [((200, 200), 25000000, 512000000, "covered"), ((20, 20), 10, 512000000, "pixel"), ((20, 20), 25000000, 1, "block")])
def test_coverage_and_budgets_fail_before_writing(fixture_dem, tmp_path, size, limit, block_limit, match):
    source, _ = fixture_dem
    output = tmp_path / "crop.tif"
    with pytest.raises(ValueError, match=match):
        extract_window(str(source), request(size), EXPECTED, output, product_id="fixture", max_pixels=limit, max_source_block_bytes=block_limit)
    assert not output.exists()


def test_site_source_bounds_respect_cosine_correction():
    bounds = site_bounds(CRS.from_proj4("+proj=eqc +R=3396190 +units=m"), request())
    assert (bounds[2]-bounds[0])*math.cos(math.radians(-4.805)) == pytest.approx(20)
    assert bounds[3]-bounds[1] == pytest.approx(20)


@pytest.mark.parametrize("kwargs", [{"center_lat": float("nan")}, {"center_lon_east": -1}, {"size_m": (6000, 20)}, {"site_id": "../outside"}])
def test_invalid_site_requests_are_rejected(kwargs):
    data = dict(site_id="BXW", center_lat=-4.805, center_lon_east=137.370, size_m=(20, 20))
    data.update(kwargs)
    with pytest.raises(ValueError):
        WindowRequest(**data)


@pytest.mark.parametrize('fill', [float('nan'), float('inf'), -float('inf')])
def test_entirely_nonfinite_source_is_rejected_before_creating_outputs(fixture_dem, tmp_path, fill):
    source, _ = fixture_dem
    # No declared nodata: invalid IEEE samples still must not count as terrain.
    with rasterio.open(source, 'r+') as src:
        src.nodata = None
        src.write(np.full((100, 100), fill, dtype='float32'), 1)
    output = tmp_path / 'invalid-window.tif'
    with pytest.raises(ValueError, match='valid elevation'):
        extract_window(str(source), request(), EXPECTED, output, product_id='invalid-fixture')
    assert not output.exists()
    assert not output.with_suffix('.provenance.json').exists()


def test_nonfinite_samples_are_masked_even_without_declared_nodata(fixture_dem, tmp_path):
    source, _ = fixture_dem
    with rasterio.open(source, 'r+') as src:
        src.nodata = None
        values = src.read(1)
        values[50, 50] = np.nan
        values[50, 51] = np.inf
        src.write(values, 1)
    output = tmp_path / 'mixed-window.tif'
    result = extract_window(str(source), request(), EXPECTED, output, product_id='mixed-fixture')
    with rasterio.open(output) as crop:
        values = crop.read(1, masked=True)
        assert np.isfinite(values.compressed()).all()
        assert np.ma.getmaskarray(values).sum() == 2
        assert result['nodata_fraction'] == pytest.approx(2 / values.size)


def test_missing_source_tiff_does_not_create_output(tmp_path):
    output = tmp_path / 'crop.tif'
    with pytest.raises(rasterio.errors.RasterioIOError):
        extract_window(str(tmp_path / 'missing.tif'), request(), EXPECTED, output, product_id='missing')
    assert not output.exists()
    assert not output.with_suffix('.provenance.json').exists()


@pytest.mark.parametrize('budget', ['max_pixels', 'max_source_block_bytes'])
@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), True, 1.5])
def test_noninteger_or_nonfinite_read_budget_cannot_bypass_limit(fixture_dem, tmp_path, budget, invalid):
    source, _ = fixture_dem
    output = tmp_path / 'crop.tif'
    with pytest.raises(ValueError, match='budget'):
        extract_window(str(source), request(), EXPECTED, output, product_id='fixture', **{budget: invalid})
    assert not output.exists()


@contextmanager
def range_server(monkeypatch, *, status=206, content_range='bytes 0-15/4096', payload=None):
    """Exercise real HTTP locally; only the transport is mapped HTTPS→loopback.

    Production HTTPS policy is not disabled, and no external endpoint is used.
    A deliberately tiny server response avoids full-download test fixtures.
    """
    if payload is None:
        payload = b'II\x2a\x00\x08\x00\x00\x00' + b'\x00' * 8
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.command, self.headers.get('Range')))
            self.send_response(status)
            self.send_header('Content-Range', content_range)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('ETag', '"local-fixture"')
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def loopback_open(req, timeout):
        assert req.full_url == 'https://fixture.invalid/raster.tif'
        local = Request(f'http://127.0.0.1:{server.server_port}/raster.tif',
                        headers=dict(req.header_items()), method=req.get_method())
        return real_urlopen(local, timeout=timeout)

    monkeypatch.setattr(fetch, 'urlopen', loopback_open)
    try:
        yield requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_real_loopback_range_response_is_accepted_with_bounded_request(monkeypatch):
    with range_server(monkeypatch) as requests:
        evidence = fetch.confirm_http_range('https://fixture.invalid/raster.tif')
    assert requests == [('GET', 'bytes=0-15')]
    assert evidence == {'status': 206, 'content_range': 'bytes 0-15/4096',
                        'etag': '"local-fixture"', 'sample_bytes': 16}


@pytest.mark.parametrize('status', [200, 403, 404, 416])
def test_server_ignoring_or_rejecting_range_fails_without_retry(monkeypatch, status):
    with range_server(monkeypatch, status=status) as requests:
        with pytest.raises((ValueError, HTTPError)):
            fetch.confirm_http_range('https://fixture.invalid/raster.tif')
    assert requests == [('GET', 'bytes=0-15')]


@pytest.mark.parametrize('content_range', ['bytes 16-31/4096', 'bytes 0-15/*',
                                          'bytes 0-15/0', 'bytes 0-15/15',
                                          'bytes 0-15/nonsense', 'items 0-15/4096'])
def test_invalid_range_support_evidence_is_rejected(monkeypatch, content_range):
    with range_server(monkeypatch, content_range=content_range):
        with pytest.raises(ValueError):
            fetch.confirm_http_range('https://fixture.invalid/raster.tif')


@pytest.mark.parametrize('payload', [b'II' + b'x' * 14, b'MM' + b'x' * 14,
                                    b'not a TIFF file!', b'II\x2a\x00'])
def test_non_tiff_and_truncated_range_payloads_are_rejected(monkeypatch, payload):
    with range_server(monkeypatch, payload=payload):
        with pytest.raises(ValueError):
            fetch.confirm_http_range('https://fixture.invalid/raster.tif')


def test_ignored_range_aborts_before_body_read(monkeypatch):
    class Response:
        status = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *_args):
            pytest.fail('Ignored Range must be rejected before reading its body')

    monkeypatch.setattr(fetch, 'urlopen', lambda *_args, **_kwargs: Response())
    with pytest.raises(ValueError, match='Range'):
        fetch.confirm_http_range('https://fixture.invalid/raster.tif')


def test_remote_range_failure_prevents_raster_open(monkeypatch, tmp_path):
    def reject_range(*_args, **_kwargs):
        raise ValueError('No Range support')

    monkeypatch.setattr(fetch, 'confirm_http_range', reject_range)
    monkeypatch.setattr(fetch.rasterio, 'open', lambda *_args, **_kwargs: pytest.fail('must not open raster'))
    output = tmp_path / 'crop.tif'
    with pytest.raises(ValueError, match='Range'):
        extract_window('https://fixture.invalid/raster.tif', request(), EXPECTED,
                       output, product_id='remote-fixture')
    assert not output.exists()
