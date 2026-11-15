"""SPICE sun table for a site (proje.md §6.4, §8.1 env_server input; D014).

For each UTC step: Sun azimuth/elevation at the site (aberration-corrected position in
IAU_MARS, local east/north/up on the sphere of the product radius) and the one-way
Mars→Earth light time. Uses the generic NAIF kernels naif0012.tls, pck00011.tpc and
de440s.bsp. Output is an immutable CSV + JSON sidecar with kernel hashes; DERIVED.
The horizon is geometric (elevation 0); local terrain horizons need the horizon cube.
"""
from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from .rad import sha256_file

KERNELS = ("naif0012.tls", "pck00011.tpc", "de440s.bsp")
# de440s carries the Mars system barycentre (4), not Mars itself (499, needs mar097.bsp).
# The barycentre-to-centre offset is far below a metre: irrelevant for the Sun's direction.
OBSERVER = "MARS BARYCENTER"


def sun_table(kernel_dir: Path, lat_deg: float, lon_east_deg: float, radius_m: float,
              start: datetime, end: datetime, step_s: float = 60.0) -> list[tuple]:
    import spiceypy as sp

    paths = [str(Path(kernel_dir) / k) for k in KERNELS]
    sp.furnsh(paths)
    try:
        site = np.array(sp.latrec(radius_m / 1000.0, math.radians(lon_east_deg), math.radians(lat_deg)))
        up = site / np.linalg.norm(site)
        east = np.cross([0.0, 0.0, 1.0], up)
        east /= np.linalg.norm(east)
        north = np.cross(up, east)
        rows = []
        t = start
        while t <= end:
            et = sp.str2et(t.strftime("%Y-%m-%dT%H:%M:%S"))
            # Inertial LT+S direction, then the body-fixed frame at the observer's epoch
            # (IAU_MARS with light time would need the 499 ephemeris).
            sun_j2000, _ = sp.spkpos("SUN", et, "J2000", "LT+S", OBSERVER)
            sun = np.array(sp.pxform("J2000", "IAU_MARS", et)) @ np.array(sun_j2000)
            v = np.array(sun) - site
            v /= np.linalg.norm(v)
            el = math.degrees(math.asin(float(np.dot(v, up))))
            az = math.degrees(math.atan2(float(np.dot(v, east)), float(np.dot(v, north)))) % 360.0
            _, lt = sp.spkpos("EARTH", et, "J2000", "NONE", OBSERVER)
            rows.append((t, az, el, lt))
            t += timedelta(seconds=step_s)
        return rows
    finally:
        sp.kclear()


def write_sun_table(kernel_dir: Path, out_csv: Path, *, site_id: str, lat_deg: float, lon_east_deg: float,
                    radius_m: float, start: datetime, end: datetime, step_s: float = 60.0) -> dict:
    out_csv, sidecar = Path(out_csv), Path(out_csv).with_suffix(".json")
    for path in (out_csv, sidecar):
        if path.exists():
            raise FileExistsError(f"{path} exists; environment tables are immutable")
    rows = sun_table(kernel_dir, lat_deg, lon_east_deg, radius_m, start, end, step_s)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["utc", "sun_az_deg", "sun_el_deg", "earth_light_time_s"])
        for t, az, el, lt in rows:
            writer.writerow([t.strftime("%Y-%m-%dT%H:%M:%SZ"), f"{az:.4f}", f"{el:.4f}", f"{lt:.3f}"])
    record = {
        "schema": "redline.sun_table.v1", "status": "DERIVED", "site_id": site_id,
        "site": {"lat_deg": lat_deg, "lon_east_deg": lon_east_deg, "radius_m": radius_m},
        "utc_range": [start.isoformat(), end.isoformat()], "step_s": step_s, "rows": len(rows),
        "kernels": {k: sha256_file(Path(kernel_dir) / k) for k in KERNELS},
        "method": "proje.md §6.4 with observer MARS BARYCENTER (de440s has no 499): spkpos SUN J2000 LT+S "
                  "rotated by pxform J2000->IAU_MARS at et; latrec sphere; ENU az/el; spkpos EARTH J2000 NONE "
                  "light time",
        "horizon": "geometric (elevation 0); terrain horizon needs the horizon cube",
        "csv_sha256": sha256_file(out_csv),
    }
    with sidecar.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(record, indent=1) + "\n")
    return record


def read_sun_table(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    """(unix seconds, az, el, light time, sidecar) after checking the recorded hash."""
    path = Path(path)
    sidecar = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if sha256_file(path) != sidecar["csv_sha256"]:
        raise ValueError(f"{path}: SHA-256 does not match its sidecar")
    t, az, el, lt = [], [], [], []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            t.append(datetime.strptime(row["utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
            az.append(float(row["sun_az_deg"]))
            el.append(float(row["sun_el_deg"]))
            lt.append(float(row["earth_light_time_s"]))
    return np.array(t), np.array(az), np.array(el), np.array(lt), sidecar
