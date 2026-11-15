"""Product-WKT checks for the specifically configured Gale EQC source.

Configuration is an expectation, never a substitute for source WKT. These
checks establish horizontal metadata consistency, not raster alignment or a
vertical datum. There is deliberately no Earth CRS fallback.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import warnings

from pyproj import CRS
from pyproj.exceptions import CRSError


@dataclass(frozen=True)
class ExpectedCrs:
    sphere_radius_m: float
    lon_0_deg: float
    lat_ts_deg: float

    def __post_init__(self):
        if not all(math.isfinite(v) for v in asdict(self).values()):
            raise ValueError("Expected CRS parameters must be finite")
        if not 3_000_000 < self.sphere_radius_m < 4_000_000:
            raise ValueError("Expected a product-specific Mars radius")


def check_wkt(wkt: str | None, expected: ExpectedCrs) -> dict:
    """Raise on missing/non-Mars/non-EQC metadata or expectation mismatch."""
    if not wkt:
        raise ValueError("Source CRS is missing; product metadata is required")
    try:
        crs = CRS.from_wkt(wkt)
    except CRSError as error:
        raise ValueError("Source contains invalid product WKT") from error
    if not crs.is_projected or crs.coordinate_operation is None:
        raise ValueError("Source must have a projected product CRS")
    if not all(axis.unit_name.lower() in ("metre", "meter") for axis in crs.axis_info[:2]):
        raise ValueError("Source horizontal units must be metres")
    a = crs.ellipsoid.semi_major_metre
    b = crs.ellipsoid.semi_minor_metre
    if not math.isclose(a, b, abs_tol=1e-5, rel_tol=0):
        raise ValueError("This Gale mapping requires the source's spherical Mars datum")
    if not math.isclose(a, expected.sphere_radius_m, abs_tol=1e-3, rel_tol=0):
        raise ValueError(f"Source radius {a} differs from configured product expectation")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parameters = crs.to_dict()
    if parameters.get("proj") != "eqc":
        raise ValueError("Expected product equirectangular projection, not a substituted CRS")
    for key, target in (("lon_0", expected.lon_0_deg), ("lat_ts", expected.lat_ts_deg), ("lat_0", 0)):
        if not math.isclose(float(parameters.get(key, 0)), target, abs_tol=1e-9, rel_tol=0):
            raise ValueError(f"Source {key} differs from expected product parameter")
    if any(float(parameters.get(k, 0)) != 0 for k in ("x_0", "y_0")):
        raise ValueError("Unexpected false easting/northing in source CRS")
    if crs.axis_info[0].direction != "east" or crs.axis_info[1].direction != "north":
        raise ValueError("Expected east/north projected axis order")
    return {
        "ok": True, "source_wkt": crs.to_wkt(), "projection": "eqc",
        "sphere_radius_m": a, "lon_0_deg": float(parameters.get("lon_0", 0)),
        "lat_ts_deg": float(parameters.get("lat_ts", 0)), "units": "m",
        "expected": asdict(expected),
        "vertical_reference": "not established by horizontal WKT; check source label",
        "alignment_verified": False,
    }
