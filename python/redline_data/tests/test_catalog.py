"""No external network: fake HEAD responses prohibit reading any body."""
from dataclasses import replace
from datetime import datetime
from email.message import Message
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest
import yaml

from redline_data import catalog


ROOT = Path(__file__).resolve().parents[3]


def _headers(**values):
    result = Message()
    for key, value in values.items():
        result[key.replace('_', '-')] = value
    return result


class Response:
    def __init__(self, status=200, headers=None):
        self.status = status
        self.headers = headers or _headers()
        self.closed = False

    def read(self, *args):
        pytest.fail("HEAD catalog must not read a response body")

    def close(self):
        self.closed = True


class Opener:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):
        assert request.get_method() == 'HEAD'
        self.requests.append((request.full_url, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def product():
    return catalog.Product('dem', 'example-dem', 'https://example.test/dem.tif',
                           catalog.ProvenanceStatus.DERIVED, ('BXW',), 'topography',
                           ('horizontal_crs', 'vertical_datum', 'alignment'))


def test_repository_configs_are_scenario_extents_and_exact_source_urls():
    sites = catalog.load_sites(ROOT / 'config/sites.yaml')
    assert sites['BXW'].size_m == (3000, 3000)
    assert sites['BXW'].center_lon_east == 137.370
    assert sites['YKB'].plan_grid_m == 4
    assert sites['BXW'].to_dict()['role'] == 'forward_eva'
    products = catalog.load_products(ROOT / 'config/products.yaml')
    assert {p.key for p in products} == {'gale_dem_v3', 'gale_lrgb', 'places_interp', 'mmgis_msl_waypoints', 'hirise_dtm_bxw_019698'}
    assert all(p.metadata_verified is False for p in products)
    assert all(p.unknown_fields for p in products)
    assert next(p for p in products if p.key == 'places_interp').url == (
        'https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_interp.csv')


def test_probe_preserves_headers_and_does_not_invent_scientific_metadata(product):
    response = Response(headers=_headers(Content_Length='5780000000', ETag='"multipart-4"',
                                        Last_Modified='Tue, 03 Nov 2026 10:00:00 GMT',
                                        Content_Type='image/tiff'))
    opener = Opener(response)
    result = catalog.probe(product, opener=opener)
    assert result.available and result.http_status == 200
    assert result.content_length == 5780000000
    assert result.etag == '"multipart-4"'
    assert result.last_modified == 'Tue, 03 Nov 2026 10:00:00 GMT'
    assert result.acquired_at is None and result.sha256 is None
    assert result.metadata_verified is False and result.status == 'DERIVED'
    assert result.unknown_fields == product.unknown_fields
    assert datetime.fromisoformat(result.checked_at).utcoffset().total_seconds() == 0
    assert response.closed and opener.requests == [(product.url, 10)]


def test_missing_optional_head_metadata_stays_unknown(product):
    result = catalog.probe(product, opener=Opener(Response()))
    assert result.available
    assert result.content_length is None and result.etag is None


@pytest.mark.parametrize('code', [204, 403, 404, 405, 429, 500, 503])
def test_http_error_is_explicit_and_has_no_get_fallback(product, code):
    error = HTTPError(product.url, code, 'error', _headers(), None)
    opener = Opener(error)
    result = catalog.probe(product, opener=opener)
    assert not result.available
    assert result.http_status == code
    assert result.error == f'http_status_{code}'
    assert len(opener.requests) == 1


@pytest.mark.parametrize('error', [URLError('unavailable'), TimeoutError('timeout'), OSError('failure')])
def test_network_errors_are_records_not_false_success(product, error):
    result = catalog.probe(product, opener=Opener(error))
    assert not result.available and result.http_status is None
    assert result.error.startswith('network_error:')


def test_bounded_redirects_keep_head_and_source_identity(product):
    first = HTTPError(product.url, 302, 'redirect', _headers(Location='/new.tif'), None)
    last = Response(headers=_headers(Content_Length='100'))
    opener = Opener(first, last)
    result = catalog.probe(product, opener=opener)
    assert result.available and result.final_url == 'https://example.test/new.tif'
    assert result.source_url == product.url
    assert len(opener.requests) == 2 and last.closed


def test_redirect_limit_prevents_retry_loop(product):
    errors = [HTTPError(product.url, 301, 'redirect', _headers(Location=product.url), None) for _ in range(3)]
    opener = Opener(*errors)
    result = catalog.probe(product, max_redirects=2, opener=opener)
    assert result.error == 'redirect_limit_exceeded'
    assert len(opener.requests) == 3


@pytest.mark.parametrize('location', ['http://example.test/data', 'https://u:p@example.test/data',
                                      'https://example.test/data?token=secret', 'https://example.test/data#fragment'])
def test_redirect_rejects_unsafe_or_credential_bearing_urls(product, location):
    error = HTTPError(product.url, 302, 'redirect', _headers(Location=location), None)
    opener = Opener(error)
    result = catalog.probe(product, opener=opener)
    assert result.error.startswith('invalid_redirect:')
    assert len(opener.requests) == 1


def test_network_failure_after_redirect_does_not_keep_previous_headers(product):
    first = HTTPError(product.url, 302, 'redirect', _headers(Location='/next', Content_Length='999'), None)
    result = catalog.probe(product, opener=Opener(first, TimeoutError('timeout')))
    assert result.http_status is None and result.content_length is None


@pytest.mark.parametrize('length', ['-1', 'abc', '1.5', '9' * 4301])
def test_invalid_content_length_does_not_crash_or_succeed(product, length):
    result = catalog.probe(product, opener=Opener(Response(headers=_headers(Content_Length=length))))
    assert result.error == 'invalid_content_length'
    assert result.content_length is None and not result.available


@pytest.mark.parametrize('kwargs', [{'timeout_s': 0}, {'timeout_s': float('inf')}, {'timeout_s': True},
                                     {'timeout_s': 61}, {'max_redirects': -1}, {'max_redirects': 6}, {'max_redirects': True}])
def test_probe_rejects_unbounded_controls_before_request(product, kwargs):
    opener = Opener()
    with pytest.raises(ValueError):
        catalog.probe(product, opener=opener, **kwargs)
    assert not opener.requests


def _write_config(tmp_path, data):
    path = tmp_path / 'config.yaml'
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    return path


@pytest.fixture
def products_data():
    return yaml.safe_load((ROOT / 'config/products.yaml').read_text(encoding='utf-8'))


def test_yaml_duplicate_keys_are_rejected(tmp_path):
    path = tmp_path / 'bad.yaml'
    path.write_text('schema_version: 1\nproducts: {}\nproducts: {}\n', encoding='utf-8')
    with pytest.raises(catalog.ConfigError, match='Duplicate YAML key'):
        catalog.load_products(path)


@pytest.mark.parametrize('bad_url', ['http://example.test/data', 'file:///tmp/data',
                                    'https://a:b@example.test/data', 'https://example.test/data?key=x',
                                    'https://example.test/data\nheader'])
def test_product_urls_are_strictly_validated(tmp_path, products_data, bad_url):
    products_data['products']['gale_dem_v3']['url'] = bad_url
    with pytest.raises(catalog.ConfigError):
        catalog.load_products(_write_config(tmp_path, products_data))


@pytest.mark.parametrize('field,value', [('metadata_verified', True), ('status', 'REAL'),
                                       ('sites', []), ('unknown_fields', []), ('sites', ['BXW', 'BXW']),
                                       ('product_id', ''), ('unexpected', 123)])
def test_product_schema_rejects_invalid_claims_or_fields(tmp_path, products_data, field, value):
    products_data['products']['gale_dem_v3'][field] = value
    with pytest.raises(catalog.ConfigError):
        catalog.load_products(_write_config(tmp_path, products_data))


@pytest.mark.parametrize('field,value', [('center_lat', 91), ('center_lon_east', -1), ('grid_m', 0),
                                       ('grid_m', True), ('size_m', [1000]), ('crs_verified', True),
                                       ('origin_enu', [0, 0, 0]), ('extent_verified', True)])
def test_site_schema_does_not_promote_unverified_crs_or_bad_extents(tmp_path, field, value):
    data = yaml.safe_load((ROOT / 'config/sites.yaml').read_text(encoding='utf-8'))
    data['sites']['BXW'][field] = value
    with pytest.raises(catalog.ConfigError):
        catalog.load_sites(_write_config(tmp_path, data))


def test_unknown_default_crs_is_rejected(tmp_path):
    data = yaml.safe_load((ROOT / 'config/sites.yaml').read_text(encoding='utf-8'))
    data['crs_default'] = {'proj': 'eqc'}
    with pytest.raises(catalog.ConfigError):
        catalog.load_sites(_write_config(tmp_path, data))


def test_build_filters_before_probing_and_serializes_errors(monkeypatch, product):
    other = replace(product, key='other', sites=('YKB',))
    monkeypatch.setattr(catalog, 'load_products', lambda path: (product, other))
    seen = []
    real_probe = catalog.probe
    def fake_probe(item, **kwargs):
        seen.append(item.key)
        return real_probe(item, opener=Opener(Response()), **kwargs)
    monkeypatch.setattr(catalog, 'probe', fake_probe)
    report = catalog.build('unused', site_id='BXW', product_keys=('dem',))
    assert report.ok and report.errors == () and seen == ['dem']
    assert json.loads(json.dumps(report.to_dict()))['entries'][0]['method'] == 'HEAD'
    with pytest.raises(catalog.ConfigError):
        catalog.build('unused', product_keys=('missing',))
    with pytest.raises(catalog.ConfigError):
        catalog.build('unused', product_keys=('dem', 'dem'))
    with pytest.raises(catalog.ConfigError):
        catalog.build('unused', site_id='UNKNOWN')


def test_report_retains_failure_and_is_not_ok(product):
    entry = catalog.probe(product, opener=Opener(Response(status=405)))
    report = catalog.CatalogReport(entry.checked_at, (entry,))
    assert not report.ok and report.errors == ('dem: http_status_405',)
    assert report.to_dict()['ok'] is False
