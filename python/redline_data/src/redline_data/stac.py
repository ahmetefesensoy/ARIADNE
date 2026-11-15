"""Local processing-time STAC for hashed Mars raster products, never Earth data.

SSYS 1.1.1's official Collection example uses a whole-target-body envelope.
We retain that conservative convention, explicitly not a footprint, because
core STAC Collection requires a bbox whereas Items can be unlocated. SSYS is
a proposal and does not explicitly replace the core WGS84 spatial wording:
generic Earth-only clients must not spatially index this Collection as Earth.
Item geometry is null; native CRS/grid/frame details remain in Projection and
REDLINE metadata. Processing dates are not source acquisition dates.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote

STAC_VERSION = "1.1.0"
SSYS = "https://stac-extensions.github.io/ssys/v1.1.1/schema.json"
PROJECTION = "https://stac-extensions.github.io/projection/v2.1.0/schema.json"
COLLECTION_SCHEMA = "https://schemas.stacspec.org/v1.1.0/collection-spec/json-schema/collection.json"
ITEM_SCHEMA = "https://schemas.stacspec.org/v1.1.0/item-spec/json-schema/item.json"


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Manifest paths must be nonempty relative POSIX paths")
    path = (root / value).resolve()
    if Path(value).is_absolute() or not path.is_relative_to(root):
        raise ValueError("Manifest asset path escapes the data root")
    if not path.is_file():
        raise ValueError(f"Manifest asset is missing: {value}")
    return path


def _href(path: Path, parent: Path) -> str:
    return quote(Path(os.path.relpath(path, parent)).as_posix(), safe="/:")


def _utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("missing timezone")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Recorded processing time must be an offset-aware timestamp") from exc
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _json(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot load metadata {path.name}") from exc
    if not isinstance(result, dict):
        raise ValueError("Manifest and provenance must be JSON objects")
    return result


def write(site_id: str, *, manifest_path: Path, destination: Path,
          root: Path | None = None) -> dict:
    """Write a Collection and one Item for each verified TIFF in a run manifest.

    ``root`` resolves the manifest's relative asset/metadata paths; callers
    should pass the checkout explicitly (default current directory). All listed
    assets must match recorded bytes/SHA256, including non-raster QA assets.
    Every excluded non-TIFF receives an explicit reason in the returned report.
    Unknown/missing raster provenance fails before output files are created.
    Existing outputs are reused only if their exact JSON bytes still match.
    No network access, external STAC publication, or raster pixel reading occurs.
    """
    import rasterio

    if not isinstance(site_id, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", site_id):
        raise ValueError("site_id must be an uppercase simple identifier")
    root = Path.cwd().resolve() if root is None else Path(root).resolve()
    destination = Path(destination).resolve()
    manifest_path = Path(manifest_path).resolve()
    manifest = _json(manifest_path)
    if manifest.get("site_id") != site_id or not isinstance(manifest.get("assets"), dict) or not manifest["assets"]:
        raise ValueError("Run manifest must identify this site and nonempty assets")
    metadata = manifest.get("metadata")
    if not isinstance(metadata, dict) or not metadata:
        raise ValueError("Run manifest requires recorded provenance metadata")
    paths = {}
    for name, record in manifest["assets"].items():
        path = _path(root, name)
        if (not isinstance(record, dict) or type(record.get("bytes")) is not int
                or path.stat().st_size != record["bytes"] or _digest(path) != record.get("sha256")):
            raise ValueError(f"Manifest asset size/hash mismatch: {name}")
        paths[name] = path
    for name, recorded in metadata.items():
        if _json(_path(root, name)) != recorded:
            raise ValueError(f"Recorded provenance differs from current sidecar: {name}")

    collection_id = f"redline-{site_id.lower()}-derived-terrain"
    documents = {}
    items = []
    omitted = []
    dates = []
    ids = set()
    for name, path in sorted(paths.items()):
        if path.suffix.lower() not in (".tif", ".tiff"):
            omitted.append({"path": name, "reason": "non-raster run artifact; retained by run-manifest asset"})
            continue
        matching = []
        for meta_name, record in metadata.items():
            meta_path = _path(root, meta_name)
            if meta_path == path.with_suffix(".provenance.json"):
                matching.append((meta_name, record, record.get("sha256")))
            elif meta_path.name == "derivatives.provenance.json":
                for asset in record.get("assets", {}).values():
                    if (meta_path.parent / asset.get("href", "")).resolve() == path:
                        matching.append((meta_name, record, asset.get("sha256")))
        if len(matching) != 1:
            raise ValueError(f"Raster requires exactly one recorded provenance sidecar: {name}")
        meta_name, record, digest = matching[0]
        if digest != manifest["assets"][name]["sha256"] or record.get("status") != "DERIVED":
            raise ValueError(f"Raster provenance status/hash mismatch: {name}")
        processed = _utc(record.get("created_at"))
        dates.append(processed)
        local = record.get("frame") == "map"
        frame_record = record
        frame_path = _path(root, meta_name)
        if local and "source_wkt" not in record:
            # Terrain derivative inherits the exact hashed local DEM frame.
            source_path = _path(root, record.get("source"))
            source_name = source_path.relative_to(root).as_posix()
            frame_path = source_path.with_suffix(".provenance.json")
            frame_name = frame_path.relative_to(root).as_posix()
            frame_record = metadata.get(frame_name)
            if (source_name not in paths or not isinstance(frame_record, dict)
                    or frame_record.get("sha256") != manifest["assets"][source_name]["sha256"]
                    or record.get("identity", {}).get("source_sha256") != frame_record.get("sha256")):
                raise ValueError("Derivative requires the exact source local DEM and frame provenance")
        with rasterio.open(path) as dataset:
            shape = [dataset.height, dataset.width]
            transform = list(dataset.transform)
            if local:
                if dataset.crs is not None or frame_record.get("frame") != "map":
                    raise ValueError("Engineering local raster must not be labelled with a source/Earth CRS")
                source_wkt = frame_record.get("source_wkt")
                if not source_wkt or not frame_record.get("origin") or not frame_record.get("east_scale_factor"):
                    raise ValueError("Local frame requires source WKT, origin and reversible mapping")
                wkt = None
            else:
                if dataset.crs is None:
                    raise ValueError("Source-window raster requires its actual product WKT")
                wkt = dataset.crs.to_wkt(version="WKT2_2019")
                source_wkt = record.get("crs_report", {}).get("source_wkt")
                if not source_wkt or dataset.crs != rasterio.crs.CRS.from_wkt(source_wkt):
                    raise ValueError("Source raster WKT differs from recorded product CRS")
            # Verify Mars metadata explicitly without choosing an Earth fallback.
            from pyproj import CRS
            body_crs = CRS.from_wkt(source_wkt)
            radius = body_crs.ellipsoid.semi_major_metre
            if not 3_000_000 < radius < 4_000_000:
                raise ValueError("STAC target Mars conflicts with recorded source CRS")
            if local and (shape != frame_record.get("shape") or transform != frame_record.get("transform")):
                raise ValueError("Local raster grid differs from engineering-frame provenance")
            if not local and (shape != record.get("shape") or transform != record.get("transform")):
                raise ValueError("Source raster grid differs from recorded provenance")
            native_bbox = list(dataset.bounds)
        item_id = f"{site_id.lower()}-{path.stem}"
        if item_id in ids:
            raise ValueError("Raster basenames must give unique Item identifiers")
        ids.add(item_id)
        item_name = f"items/{item_id}.json"
        item_dir = destination / "items"
        properties = {"datetime": processed, "created": processed,
            "ssys:targets": ["Mars"], "ssys:target_class": "planet",
            "proj:code": None, "proj:wkt2": wkt, "proj:shape": shape,
            "proj:transform": transform, "proj:bbox": native_bbox,
            "redline:status": "DERIVED", "redline:site_id": site_id,
            "redline:datetime_kind": "processing", "redline:acquired_at": None,
            "redline:alignment_verified": False,
            "redline:geometry_reason": "Mars native/engineering data; no WGS84 footprint asserted",
            "redline:vertical_reference": frame_record.get("vertical_reference", record.get("crs_report", {}).get("vertical_reference", "unverified"))}
        if local:
            properties.update({"redline:frame": "map", "redline:source_wkt2": source_wkt,
                "redline:local_mapping": {key: frame_record[key] for key in ("origin", "east_scale_factor")},
                "redline:frame_kind": "local affine approximation, not geodetic ENU"})
        item = {"stac_version": STAC_VERSION, "stac_extensions": [SSYS, PROJECTION],
            "type": "Feature", "id": item_id, "collection": collection_id, "geometry": None,
            "properties": properties,
            "links": [{"rel": "collection", "href": "../collection.json", "type": "application/json"},
                      {"rel": "root", "href": "../collection.json", "type": "application/json"}],
            "assets": {"data": {"href": _href(path, item_dir), "type": "image/tiff; application=geotiff",
                "roles": ["data"], "redline:sha256": digest, "redline:status": "DERIVED"},
                "provenance": {"href": _href(_path(root, meta_name), item_dir), "type": "application/json",
                    "roles": ["metadata"], "redline:sha256": _digest(_path(root, meta_name))}}}
        if frame_path != _path(root, meta_name):
            item["assets"]["frame_metadata"] = {"href": _href(frame_path, item_dir), "type": "application/json",
                "roles": ["metadata"], "redline:sha256": _digest(frame_path)}
        documents[item_name] = item
        items.append(item_name)
    if not items:
        raise ValueError("Run manifest has no catalogable raster assets")
    collection = {"stac_version": STAC_VERSION, "stac_extensions": [SSYS], "type": "Collection",
        "id": collection_id, "title": f"REDLINE {site_id} derived terrain processing outputs",
        "description": "Local processing-time catalog for Mars. Core Item geometry is null; native grids and local engineering-frame metadata carry spatial context. No Earth footprint, acquisition-time or independent accuracy claim.",
        "license": "other", "ssys:targets": ["Mars"], "ssys:target_class": "planet",
        "extent": {"spatial": {"bbox": [[-180, -90, 180, 90]]}, "temporal": {"interval": [[min(dates), max(dates)]]}},
        "redline:extent_kind": "conservative_target_body_envelope_not_footprint",
        "redline:extent_convention": "SSYS 1.1.1 official Collection example; proposal extension does not explicitly override core WGS84 wording. Do not spatially index as Earth.",
        "redline:extent_reference": "https://raw.githubusercontent.com/stac-extensions/ssys/v1.1.1/examples/collection.json",
        "redline:datetime_kind": "processing", "redline:acquired_at": None,
        "redline:license_note": "Source product licensing remains unresolved; no redistribution rights granted by this catalog.",
        "links": [{"rel": "item", "href": item, "type": "application/geo+json"} for item in items],
        "assets": {"run_manifest": {"href": _href(manifest_path, destination), "type": "application/json",
            "roles": ["metadata"], "redline:sha256": _digest(manifest_path)}}}
    documents["collection.json"] = collection
    report = {"site_id": site_id, "is_stac_collection": True, "collection": "collection.json",
        "items": items, "uncataloged_assets": omitted, "source_manifest_sha256": _digest(manifest_path),
        "schema_versions": {"core": STAC_VERSION, "projection": "2.1.0", "ssys": "1.1.1"},
        "scope": "processing-time catalog; acquisition unknown; vertical reference from source provenance/extra evidence, no independent accuracy claim; no Earth footprint or alignment claim",
        "planetary_convention_limit": collection["redline:extent_convention"]}
    documents["stac_report.json"] = report
    encoded = {name: json.dumps(document, indent=2, allow_nan=False) + "\n" for name, document in documents.items()}
    if destination.exists():
        files = {p.relative_to(destination).as_posix(): p for p in destination.rglob("*") if p.is_file()}
        if files:
            if set(files) != set(encoded) or any(files[name].read_text(encoding="utf-8") != text for name, text in encoded.items()):
                raise ValueError("Existing STAC directory differs; use a new output path")
            return report
    for name, text in encoded.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    return report


def validate(destination: Path, *, schema_root: Path) -> dict:
    """Validate Collection/Items against hash-pinned official schemas offline.

    The caller explicitly supplies the checkout's schema fixture directory.
    No remote resolver is used; missing/unknown resources fail closed. This
    validates JSON/schema and REDLINE planetary/time semantics, not asset pixel
    accuracy. Asset hashes are checked during write(); here the catalog JSON
    hashes and schema ledger are recorded for reproducible validation evidence.
    """
    import jsonschema
    from referencing import Registry, Resource
    from referencing.exceptions import NoSuchResource

    schema_root = Path(schema_root).resolve()
    destination = Path(destination).resolve()
    ledger = _json(schema_root / "manifest.json")
    records = ledger.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("Schema ledger must contain hash-pinned files")
    resources = {}
    schema_hashes = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid schema ledger entry")
        path = _path(schema_root, record.get("path"))
        digest = _digest(path)
        if digest != record.get("sha256"):
            raise ValueError(f"Schema fixture hash mismatch: {path.name}")
        schema_hashes[record["path"]] = digest
        if record.get("kind") == "license":
            continue
        content = _json(path)
        resource = Resource.from_contents(content)
        uri = record.get("url")
        if not isinstance(uri, str) or not uri.startswith("https://") or uri in resources:
            raise ValueError("Schema ledger has invalid/duplicate URI")
        resources[uri] = resource
        declared = content.get("$id")
        if declared:
            resources[declared.rstrip("#")] = resource

    def no_network(uri):
        raise NoSuchResource(ref=uri)

    registry = Registry(retrieve=no_network).with_resources(resources.items())
    collection_path = _path(destination, "collection.json")
    collection = _json(collection_path)
    if collection.get("type") != "Collection":
        raise ValueError("Expected a STAC Collection")
    if (collection.get("extent", {}).get("spatial", {}).get("bbox") != [[-180, -90, 180, 90]]
            or collection.get("redline:extent_kind") != "conservative_target_body_envelope_not_footprint"
            or not collection.get("redline:extent_convention")):
        raise ValueError("Collection must retain the explicit conservative target-body extent convention")
    item_paths = []
    for link in collection.get("links", []):
        if isinstance(link, dict) and link.get("rel") == "item":
            href = link.get("href")
            if not isinstance(href, str) or "%" in href or ":" in href or "?" in href or "#" in href:
                raise ValueError("Item links must use local plain relative paths")
            item_paths.append(_path(destination, href))
    if not item_paths or len(set(item_paths)) != len(item_paths):
        raise ValueError("Collection requires distinct local Item links")
    documents = [(collection_path, collection, COLLECTION_SCHEMA)]
    documents.extend((path, _json(path), ITEM_SCHEMA) for path in item_paths)
    document_hashes = {}
    schemas_used = set()
    item_ids = set()
    for path, document, core in documents:
        schemas = [core, *document.get("stac_extensions", [])]
        for uri in schemas:
            if uri not in resources:
                raise ValueError(f"Uncached schema: {uri}; network retrieval is disabled")
            try:
                validator = jsonschema.Draft7Validator(resources[uri].contents,
                    registry=registry, format_checker=jsonschema.FormatChecker())
                validator.validate(document)
            except Exception as exc:
                raise ValueError(f"STAC schema validation failed for {path.name}: {exc}") from exc
            schemas_used.add(uri)
        fields = document if document.get("type") == "Collection" else document["properties"]
        if (SSYS not in document.get("stac_extensions", []) or fields.get("ssys:targets") != ["Mars"]
                or fields.get("redline:datetime_kind") != "processing" or fields.get("redline:acquired_at", "missing") is not None):
            raise ValueError("Catalog must retain explicit Mars target and processing-not-acquisition time semantics")
        if document.get("type") == "Feature":
            if (document.get("geometry") is not None or "bbox" in document
                    or document.get("collection") != collection["id"]
                    or document["id"] in item_ids or PROJECTION not in document.get("stac_extensions", [])
                    or fields.get("proj:code", "missing") is not None):
                raise ValueError("Item identity, geometry or projection violates REDLINE planetary contract")
            item_ids.add(document["id"])
            if fields.get("redline:frame") == "map" and (fields.get("proj:wkt2") is not None
                    or not fields.get("redline:source_wkt2") or not fields.get("redline:local_mapping")):
                raise ValueError("Local frame must retain source mapping without source-CRS relabelling")
        document_hashes[path.relative_to(destination).as_posix()] = _digest(path)
    return {"ok": True, "items_validated": len(item_paths), "documents_validated": len(documents),
        "schema_versions": {"core": STAC_VERSION, "projection": "2.1.0", "ssys": "1.1.1"},
        "schemas_used": sorted(schemas_used), "schema_fixture_hashes": schema_hashes,
        "schema_manifest_sha256": _digest(schema_root / "manifest.json"),
        "document_sha256": document_hashes, "network_retrieval": False,
        "scope": "Schema and explicit Mars/processing-time semantics only; asset hashes checked by writer, no pixel accuracy validation",
        "planetary_convention_limit": collection.get("redline:extent_convention")}
