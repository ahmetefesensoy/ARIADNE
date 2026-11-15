"""Offline STAC schema and Mars/source-lineage regression tests."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

import pytest

np = pytest.importorskip("numpy")
rasterio = pytest.importorskip("rasterio")
pytest.importorskip("pyproj")
jsonschema = pytest.importorskip("jsonschema")
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from rasterio.transform import from_origin

from redline_data import stac
from redline_data.crs import ExpectedCrs
from redline_data.derive import write_products
from redline_data.enu import to_local
from redline_data.fetch import WindowRequest, extract_window


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def schema_registry():
    directory = Path(__file__).parent / "schemas"
    manifest = read(directory / "manifest.json")
    resources = {}
    for entry in manifest["files"]:
        path = directory / entry["path"]
        assert sha(path) == entry["sha256"]
        if entry.get("kind") == "license":
            continue
        content = read(path)
        resource = Resource.from_contents(content)
        resources[entry["url"]] = resource
        # STAC common.json's upstream $id contains a typo (commonjson).
        # Register both retrieval URL and declared ID, preserving upstream bytes.
        resources[content["$id"].rstrip("#")] = resource

    def prohibit_network(uri):
        raise NoSuchResource(ref=uri)

    return Registry(retrieve=prohibit_network).with_resources(resources.items()), resources


def validate(document, registry_and_resources, core_schema):
    registry, resources = registry_and_resources
    for schema_url in [core_schema, *document.get("stac_extensions", [])]:
        validator = jsonschema.Draft7Validator(resources[schema_url].contents,
            registry=registry, format_checker=jsonschema.FormatChecker())
        validator.validate(document)


@pytest.fixture
def run(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    source = root / "original.tif"
    values = np.indices((100, 100)).sum(axis=0).astype("float32")
    with rasterio.open(source, "w", driver="GTiff", count=1, height=100, width=100,
                       dtype="float32", nodata=np.nan, transform=from_origin(-50, 50, 1, 1),
                       crs="+proj=eqc +R=3396190 +units=m +type=crs") as dataset:
        dataset.write(values, 1)
    source_window = root / "window.tif"
    expected = ExpectedCrs(3396190, 0, 0)
    extract_window(str(source), WindowRequest("BXW", 0, 0, (30, 30)),
                   expected, source_window, product_id="offline-fixture")
    local = root / "local.tif"
    to_local(source_window, center_lat=0, center_lon_east=0, h0_m=0,
             resolution_m=1, destination=local, expected=expected, size_m=(20, 20))
    terrain = root / "terrain"
    terrain_meta = write_products(local, terrain)
    # Source field in actual CLI pipeline is checkout-relative. Do the same
    # without changing the generated derived data or hashes.
    metadata = {}
    for path in (source_window.with_suffix('.provenance.json'), local.with_suffix('.provenance.json'),
                 terrain / 'derivatives.provenance.json'):
        value = read(path)
        if 'source' in value:
            value['source'] = Path(value['source']).relative_to(root).as_posix()
            path.write_text(json.dumps(value), encoding='utf-8')
        metadata[path.relative_to(root).as_posix()] = value
    note = root / "qa.html"
    note.write_text("Offline synthetic numerical QA", encoding="utf-8")
    paths = [source_window, local, note, *(terrain / asset['href'] for asset in terrain_meta['assets'].values())]
    manifest = {"site_id": "BXW", "created_at": "2026-11-14T10:30:00Z", "metadata": metadata,
        "assets": {p.relative_to(root).as_posix(): {"sha256": sha(p), "bytes": p.stat().st_size} for p in paths}}
    path = root / "run_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return root, path, root / "catalog"


def test_outputs_pass_pinned_core_projection_and_ssys_schemas_without_network(run, schema_registry):
    root, manifest, output = run
    report = stac.write("BXW", manifest_path=manifest, destination=output, root=root)
    collection = read(output / report['collection'])
    validate(collection, schema_registry, stac.COLLECTION_SCHEMA)
    assert len(report['items']) == 5
    for path in report['items']:
        validate(read(output / path), schema_registry, stac.ITEM_SCHEMA)
    assert report['uncataloged_assets'] == [{'path': 'qa.html', 'reason': 'non-raster run artifact; retained by run-manifest asset'}]


def test_mars_and_local_coordinates_are_not_relabelled_earth(run):
    root, manifest, output = run
    result = stac.write("BXW", manifest_path=manifest, destination=output, root=root)
    collection = read(output / 'collection.json')
    assert collection['ssys:targets'] == ['Mars']
    assert collection['extent']['spatial']['bbox'] == [[-180, -90, 180, 90]]
    assert collection['redline:extent_kind'] == 'conservative_target_body_envelope_not_footprint'
    assert 'does not explicitly override core WGS84' in result['planetary_convention_limit']
    for name in result['items']:
        item = read(output / name)
        properties = item['properties']
        assert item['geometry'] is None and 'bbox' not in item
        assert properties['ssys:targets'] == ['Mars']
        assert properties['redline:alignment_verified'] is False
        assert properties['proj:code'] is None
        if name.endswith('window.json'):
            assert '3396190' in properties['proj:wkt2']
        else:
            assert properties['proj:wkt2'] is None
            assert properties['redline:frame'] == 'map'
            assert '3396190' in properties['redline:source_wkt2']
            assert properties['redline:local_mapping']['origin']['status'] == 'SCENARIO'


def test_processing_times_are_recorded_and_never_masquerade_as_acquisition(run):
    root, manifest, output = run
    report = stac.write("BXW", manifest_path=manifest, destination=output, root=root)
    actual_dates = []
    for name in report['items']:
        item = read(output / name)
        props = item['properties']
        provenance = read((output / name).parent / unquote(item['assets']['provenance']['href']))
        assert datetime.fromisoformat(props['datetime'].replace('Z', '+00:00')) == datetime.fromisoformat(provenance['created_at'])
        assert props['redline:datetime_kind'] == 'processing'
        assert props['redline:acquired_at'] is None
        assert props['redline:status'] == 'DERIVED'
        actual_dates.append(props['datetime'])
    assert read(output / 'collection.json')['extent']['temporal']['interval'] == [[min(actual_dates), max(actual_dates)]]


def test_all_item_asset_links_are_local_existing_and_match_hashes(run):
    root, manifest, output = run
    report = stac.write("BXW", manifest_path=manifest, destination=output, root=root)
    for name in report['items']:
        path = output / name
        for asset in read(path)['assets'].values():
            linked = (path.parent / unquote(asset['href'])).resolve()
            assert linked.is_relative_to(root) and linked.is_file()
            assert sha(linked) == asset['redline:sha256']


def test_catalog_repeated_write_is_exact_and_changed_document_is_rejected(run):
    root, manifest, output = run
    first = stac.write("BXW", manifest_path=manifest, destination=output, root=root)
    before = {p: p.stat().st_mtime_ns for p in output.rglob('*') if p.is_file()}
    assert stac.write("BXW", manifest_path=manifest, destination=output, root=root) == first
    assert {p: p.stat().st_mtime_ns for p in before} == before
    (output / 'collection.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='differs'):
        stac.write("BXW", manifest_path=manifest, destination=output, root=root)


@pytest.mark.parametrize('change', ['asset', 'missing', 'sidecar', 'metadata_snapshot', 'status', 'naive_time'])
def test_broken_lineage_fails_before_writing_catalog(run, change):
    root, manifest_path, output = run
    manifest = read(manifest_path)
    if change == 'asset':
        (root / 'window.tif').write_bytes(b'tampered')
    elif change == 'missing':
        (root / 'window.tif').unlink()
    elif change == 'metadata_snapshot':
        manifest['metadata']['window.provenance.json']['status'] = 'ARCHIVE'
    else:
        sidecar = root / 'window.provenance.json'
        value = read(sidecar)
        if change == 'sidecar':
            value['unexpected'] = True
        elif change == 'status':
            value['status'] = 'ARCHIVE'
            manifest['metadata']['window.provenance.json'] = value
        elif change == 'naive_time':
            value['created_at'] = '2026-11-14T12:00:00'
            manifest['metadata']['window.provenance.json'] = value
        sidecar.write_text(json.dumps(value), encoding='utf-8')
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError):
        stac.write('BXW', manifest_path=manifest_path, destination=output, root=root)
    assert not output.exists()


def test_manifest_paths_cannot_escape_checkout(run):
    root, manifest_path, output = run
    manifest = read(manifest_path)
    manifest['assets']['../outside.tif'] = {'bytes': 0, 'sha256': '0'*64}
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='escapes'):
        stac.write('BXW', manifest_path=manifest_path, destination=output, root=root)
    assert not output.exists()


def test_schema_validation_detects_missing_datetime_and_invented_earth_geometry(run, schema_registry):
    root, manifest, output = run
    report = stac.write('BXW', manifest_path=manifest, destination=output, root=root)
    item = read(output / report['items'][0])
    broken = deepcopy(item)
    del broken['properties']['datetime']
    with pytest.raises(jsonschema.ValidationError):
        validate(broken, schema_registry, stac.ITEM_SCHEMA)
    # Null geometry paired with an invented bbox is invalid even before semantic review.
    broken = deepcopy(item)
    broken['bbox'] = [137, -5, 138, -4]
    with pytest.raises(jsonschema.ValidationError):
        validate(broken, schema_registry, stac.ITEM_SCHEMA)


def test_offline_registry_refuses_unknown_schema_resources(schema_registry):
    registry, _ = schema_registry
    with pytest.raises(Exception):
        registry.resolver().lookup('https://example.invalid/not-vendored.json')


def test_production_validator_uses_pinned_schemas_and_records_document_hashes(run):
    root, manifest, output = run
    written = stac.write('BXW', manifest_path=manifest, destination=output, root=root)
    result = stac.validate(output, schema_root=Path(__file__).parent / 'schemas')
    assert result['ok'] and result['items_validated'] == len(written['items'])
    assert result['documents_validated'] == len(written['items']) + 1
    assert result['network_retrieval'] is False
    for name, digest in result['document_sha256'].items():
        assert digest == sha(output / name)


@pytest.mark.parametrize('change', ['missing_datetime', 'unknown_extension', 'earth_target',
                                   'source_crs_on_local', 'acquisition_claim'])
def test_production_validator_rejects_corrupt_items_without_fetching_remote_resources(run, change):
    root, manifest, output = run
    written = stac.write('BXW', manifest_path=manifest, destination=output, root=root)
    path = next(output / name for name in written['items'] if name.endswith('-local.json'))
    item = read(path)
    if change == 'missing_datetime':
        del item['properties']['datetime']
    elif change == 'unknown_extension':
        item['stac_extensions'].append('https://example.invalid/remote-schema.json')
    elif change == 'earth_target':
        item['properties']['ssys:targets'] = ['Earth']
    elif change == 'source_crs_on_local':
        item['properties']['proj:wkt2'] = item['properties']['redline:source_wkt2']
    else:
        item['properties']['redline:datetime_kind'] = 'acquisition'
    path.write_text(json.dumps(item), encoding='utf-8')
    with pytest.raises(ValueError):
        stac.validate(output, schema_root=Path(__file__).parent / 'schemas')


def test_production_validator_rejects_schema_tampering_before_use(run, tmp_path):
    import shutil
    root, manifest, output = run
    stac.write('BXW', manifest_path=manifest, destination=output, root=root)
    schema_dir = tmp_path / 'schemas'
    shutil.copytree(Path(__file__).parent / 'schemas', schema_dir)
    first = next(record for record in read(schema_dir / 'manifest.json')['files'] if record.get('kind') != 'license')
    (schema_dir / first['path']).write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='hash mismatch'):
        stac.validate(output, schema_root=schema_dir)


def test_standalone_comparison_sidecar_can_be_cataloged_without_fake_single_source_identity(run):
    import shutil
    root, manifest_path, output = run
    manifest = read(manifest_path)
    path = root / 'dtm_difference.tif'
    shutil.copyfile(root / 'local.tif', path)
    frame = manifest['metadata']['local.provenance.json']
    record = {key: frame[key] for key in ('source_wkt', 'origin', 'east_scale_factor', 'shape', 'transform')}
    record.update({'frame': 'map', 'status': 'DERIVED', 'sha256': sha(path), 'created_at': frame['created_at'],
                   'identity': {'source_pair_sha256': ['0' * 64, '1' * 64]}})
    sidecar = path.with_suffix('.provenance.json')
    sidecar.write_text(json.dumps(record), encoding='utf-8')
    manifest['metadata'][sidecar.name] = record
    manifest['assets'][path.name] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    report = stac.write('BXW', manifest_path=manifest_path, destination=output, root=root)
    assert 'items/bxw-dtm_difference.json' in report['items']
    assert stac.validate(output, schema_root=Path(__file__).parent / 'schemas')['items_validated'] == 6
