"""Validated catalog configuration and bounded HEAD-only availability probes.

No raster/CSV/JSON body is downloaded. HEAD metadata is not scientific metadata:
ETag is not a content SHA256, Last-Modified is not acquisition time, and HTTP 200
does not establish Mars CRS, footprint overlap, or pixel alignment.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
import math
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import yaml


class ConfigError(ValueError):
    """A catalog/site file does not satisfy the explicitly supported schema."""


class ProvenanceStatus(StrEnum):
    ARCHIVE = "ARCHIVE"
    DERIVED = "DERIVED"
    SIMULATED = "SIMULATED"
    SCENARIO = "SCENARIO"


@dataclass(frozen=True)
class Product:
    key: str
    product_id: str
    url: str
    status: ProvenanceStatus
    sites: tuple[str, ...]
    decision_role: str
    unknown_fields: tuple[str, ...]
    metadata_verified: bool = False


@dataclass(frozen=True)
class Site:
    site_id: str
    name: str
    center_lat: float
    center_lon_east: float
    size_m: tuple[float, float]
    grid_m: float
    plan_grid_m: float
    engine_grid_m: float
    role: str
    hirise_dtms: tuple[str, ...]
    ops_box: dict[str, Any] | None = None
    validation_campaign_sols: tuple[int, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CatalogEntry:
    key: str
    product_id: str
    status: str
    source_url: str
    final_url: str
    checked_at: str
    http_status: int | None
    available: bool
    error: str | None
    content_length: int | None
    etag: str | None
    last_modified: str | None
    content_type: str | None
    unknown_fields: tuple[str, ...]
    metadata_verified: bool = False
    acquired_at: None = None
    sha256: None = None
    method: str = "HEAD"


@dataclass(frozen=True)
class CatalogReport:
    checked_at: str
    entries: tuple[CatalogEntry, ...]
    schema_version: int = 1

    @property
    def ok(self) -> bool:
        return bool(self.entries) and all(entry.available for entry in self.entries)

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(f"{entry.key}: {entry.error}" for entry in self.entries if entry.error)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "ok": self.ok, "errors": list(self.errors)}


class _UniqueLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys instead of silently choosing the last value."""


def _unique_mapping(loader: _UniqueLoader, node: yaml.MappingNode, deep: bool = False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ConfigError("YAML mapping keys must be strings")
        if key in result:
            raise ConfigError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _load(path: str | Path, collection: str) -> dict[str, Any]:
    try:
        raw = Path(path).read_bytes()
        if len(raw) > 1_000_000:
            raise ConfigError("Configuration exceeds 1 MB limit")
        data = yaml.load(raw.decode("utf-8"), Loader=_UniqueLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot read configuration {path}: {exc}") from exc
    if not isinstance(data, dict) or set(data) != {"schema_version", collection}:
        raise ConfigError(f"Expected only schema_version and {collection}")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ConfigError("Unsupported schema_version; expected integer 1")
    records = data[collection]
    if not isinstance(records, dict) or not records or len(records) > 32:
        raise ConfigError(f"{collection} must contain 1..32 records")
    return records


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ConfigError(f"{field} must be a nonempty trimmed string")
    return value


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{field} must be a nonempty list")
    items = tuple(_string(item, field) for item in value)
    if len(set(items)) != len(items):
        raise ConfigError(f"{field} contains duplicates")
    return items


def _https_url(value: Any) -> str:
    url = _string(value, "url")
    try:
        parts = urlsplit(url)
        _ = parts.port
    except ValueError as exc:
        raise ConfigError("Invalid URL") from exc
    if (parts.scheme != "https" or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.fragment or parts.query
            or any(ord(char) < 33 or ord(char) == 127 for char in url)):
        raise ConfigError("URL must use HTTPS without credentials, query, fragment or whitespace")
    return url


def _number(value: Any, field: str, *, positive: bool = True) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ConfigError(f"{field} must be finite numeric data")
    if positive and value <= 0:
        raise ConfigError(f"{field} must be positive")
    return float(value)


def _pair(value: Any, field: str, *, positive: bool = True) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ConfigError(f"{field} requires exactly two values")
    return tuple(_number(item, field, positive=positive) for item in value)


def load_products(path: str | Path) -> tuple[Product, ...]:
    """Load product identities; metadata stays explicitly unverified in this stage."""
    required = {"product_id", "url", "status", "sites", "decision_role", "unknown_fields", "metadata_verified"}
    products = []
    for key, value in _load(path, "products").items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ConfigError(f"Invalid product key: {key}")
        if not isinstance(value, dict) or set(value) != required:
            raise ConfigError(f"{key}: missing or unexpected product fields")
        if value["metadata_verified"] is not False:
            raise ConfigError(f"{key}: this catalog stage requires unverified metadata")
        try:
            status = ProvenanceStatus(value["status"])
        except (ValueError, TypeError) as exc:
            raise ConfigError(f"{key}: invalid provenance status") from exc
        products.append(Product(key, _string(value["product_id"], "product_id"),
                                _https_url(value["url"]), status,
                                _strings(value["sites"], "sites"),
                                _string(value["decision_role"], "decision_role"),
                                _strings(value["unknown_fields"], "unknown_fields")))
    return tuple(products)


def load_sites(path: str | Path) -> dict[str, Site]:
    """Read scenario extents without accepting a guessed product CRS or origin."""
    required = {"name", "center_lat", "center_lon_east", "size_m", "grid_m", "plan_grid_m", "engine_grid_m", "role", "provenance_status", "origin_enu", "crs_verified", "extent_verified", "hirise_dtms"}
    sites = {}
    for key, value in _load(path, "sites").items():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ConfigError(f"Invalid site ID: {key}")
        if not isinstance(value, dict) or not required.issubset(value) or set(value) - required - {"ops_box", "validation_campaign_sols"}:
            raise ConfigError(f"{key}: missing or unexpected site fields")
        if (value["provenance_status"] != "SCENARIO" or value["origin_enu"] is not None
                or value["crs_verified"] is not False or value["extent_verified"] is not False):
            raise ConfigError(f"{key}: site origin, CRS and extent require separate product validation")
        lat = _number(value["center_lat"], "center_lat", positive=False)
        lon = _number(value["center_lon_east"], "center_lon_east", positive=False)
        if not -90 <= lat <= 90 or not 0 <= lon < 360:
            raise ConfigError(f"{key}: expected latitude [-90,90] and east longitude [0,360)")
        size = _pair(value["size_m"], "size_m")
        grids = tuple(_number(value[field], field) for field in ("grid_m", "plan_grid_m", "engine_grid_m"))
        if any(grid > min(size) for grid in grids):
            raise ConfigError(f"{key}: grid spacing exceeds site extent")
        ops = value.get("ops_box")
        if ops is not None:
            if not isinstance(ops, dict) or set(ops) != {"size_m", "center_offset_m", "grid_m"}:
                raise ConfigError(f"{key}: invalid ops_box")
            ops_size = _pair(ops["size_m"], "ops_box.size_m")
            offset = _pair(ops["center_offset_m"], "ops_box.center_offset_m", positive=False)
            ops_grid = _number(ops["grid_m"], "ops_box.grid_m")
            if ops_grid > min(ops_size) or any(abs(offset[i]) + ops_size[i] / 2 > size[i] / 2 for i in (0, 1)):
                raise ConfigError(f"{key}: ops_box exceeds site extent or has invalid grid")
            ops = {"size_m": ops_size, "center_offset_m": offset, "grid_m": ops_grid}
        sols = value.get("validation_campaign_sols")
        if sols is not None:
            if (not isinstance(sols, list) or len(sols) != 2 or any(type(sol) is not int or sol < 0 for sol in sols)
                    or sols[1] < sols[0]):
                raise ConfigError(f"{key}: invalid campaign sol interval")
            sols = tuple(sols)
        sites[key] = Site(key, _string(value["name"], "name"), lat, lon, size, *grids,
                          _string(value["role"], "role"), _strings(value["hirise_dtms"], "hirise_dtms"), ops, sols)
    return sites


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def probe(product: Product, *, timeout_s: float = 10, max_redirects: int = 3, opener=None) -> CatalogEntry:
    """HEAD once per hop, at most max_redirects+1 requests; never read a body.

    Timeout is per hop. The maximum catalog has 32 products; there are no retries
    or fallback GETs. HTTPS redirects are followed explicitly and capped.
    """
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 60:
        raise ValueError("timeout_s must be within (0, 60]")
    if type(max_redirects) is not int or not 0 <= max_redirects <= 5:
        raise ValueError("max_redirects must be integer 0..5")
    url = _https_url(product.url)
    client = opener if opener is not None else build_opener(_NoRedirect())
    checked = _utc_now()
    code = None
    headers = {}
    error = None
    for hop in range(max_redirects + 1):
        response = None
        code = None
        headers = {}
        try:
            response = client.open(Request(url, method="HEAD", headers={"User-Agent": "REDLINE-catalog/0.1 (HEAD only)"}), timeout=timeout_s)
            code = response.status
            headers = dict(response.headers)
        except HTTPError as exc:
            response = exc
            code = exc.code
            headers = dict(exc.headers) if exc.headers is not None else {}
        except (URLError, TimeoutError, OSError) as exc:
            error = f"network_error: {exc}"
            break
        finally:
            if response is not None:
                response.close()
        normalized = {key.lower(): value for key, value in headers.items()}
        if code in (301, 302, 303, 307, 308):
            location = normalized.get("location")
            if not location:
                error = "redirect_missing_location"
                break
            if hop == max_redirects:
                error = "redirect_limit_exceeded"
                break
            try:
                url = _https_url(urljoin(url, location))
            except ConfigError as exc:
                error = f"invalid_redirect: {exc}"
                break
            continue
        if code != 200:
            error = f"http_status_{code}"
        break
    normalized = {key.lower(): value for key, value in headers.items()}
    length = normalized.get("content-length")
    content_length = None
    if length is not None:
        if len(length.strip()) <= 20 and re.fullmatch(r"[0-9]+", length.strip()):
            content_length = int(length)
        elif error is None:
            error = "invalid_content_length"
    return CatalogEntry(product.key, product.product_id, product.status.value,
                        product.url, url, checked, code, code == 200 and error is None,
                        error, content_length, normalized.get("etag"),
                        normalized.get("last-modified"), normalized.get("content-type"),
                        product.unknown_fields)


def build(products_path: str | Path, *, site_id: str | None = None,
          product_keys: tuple[str, ...] | None = None,
          timeout_s: float = 10, max_redirects: int = 3) -> CatalogReport:
    """Return availability/provenance records, preserving every explicit error."""
    products = load_products(products_path)
    if site_id is not None:
        products = tuple(product for product in products if site_id in product.sites)
        if not products:
            raise ConfigError(f"No configured products for site {site_id}")
    if product_keys is not None:
        if not product_keys or len(set(product_keys)) != len(product_keys):
            raise ConfigError("product_keys must be nonempty and unique")
        available = {product.key for product in products}
        missing = set(product_keys) - available
        if missing:
            raise ConfigError(f"Products not configured for this site: {', '.join(sorted(missing))}")
        products = tuple(product for product in products if product.key in product_keys)
    return CatalogReport(_utc_now(), tuple(probe(product, timeout_s=timeout_s, max_redirects=max_redirects)
                                          for product in products))
