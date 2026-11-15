"""Build (or verify) the BXW SPICE sun table for S1 and check it (proje.md §6.4; D014).

Downloads the generic NAIF kernels of proje.md §6 into data/raw/spice/ when missing and
checks them against the SHA256 values pinned below, writes data/env/sun_BXW_2024-05-19_22.csv
(+ .json) if it does not exist, then writes docs/verification/T6_SPICE.json: LMST (Mars24)
against every RAD START_OBS_MARS stamp of sol 4190, noon elevation/azimuth, sunset time.
Needs the RAD files of scripts/fetch_rad.py. Run inside the REDLINE venv.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from fetch_rad import fetch
from redline_core.solar import format_hours, lmst_hours, next_sunset
from redline_data.rad import parse_doy_utc, sha256_file
from redline_data.spice_env import KERNELS, read_sun_table, write_sun_table

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data/env/sun_BXW_2024-05-19_22.csv"
RAD = ROOT / "data/raw/env/rad/RAD_RDR_2024_140_18_30_4190_V00.TXT"
SITE = {"lat_deg": -4.805, "lon_east_deg": 137.370, "radius_m": 3396190.0}  # sites.yaml, Gale eqc sphere
MSL_LMST_LON = 137.4417  # MSL LMST is defined at the landing site
NAIF = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/"
# proje.md §6 sources; hashes of the files the D014 table was built from (2026-11-14).
KERNEL_SOURCES = {
    "naif0012.tls": ("lsk/naif0012.tls", "678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b"),
    "pck00011.tpc": ("pck/pck00011.tpc", "3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1"),
    "de440s.bsp": ("spk/planets/de440s.bsp", "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"),
}


def fetch_kernels(kernel_dir: Path) -> None:
    kernel_dir.mkdir(parents=True, exist_ok=True)
    for name in KERNELS:
        url, expected = KERNEL_SOURCES[name]
        fetch(NAIF + url, kernel_dir / name)
        observed = sha256_file(kernel_dir / name)
        if observed != expected:
            raise SystemExit(f"{name}: SHA256 {observed} != pinned {expected}; NAIF file changed or download broke")


def main() -> int:
    fetch_kernels(ROOT / "data/raw/spice")
    if not TABLE.exists():
        write_sun_table(ROOT / "data/raw/spice", TABLE, site_id="BXW", **SITE,
                        start=datetime(2024, 5, 19, 12, tzinfo=timezone.utc),
                        end=datetime(2024, 5, 22, 12, tzinfo=timezone.utc), step_s=60.0)
    t, az, el, lt, meta = read_sun_table(TABLE)
    pairs, mars = [], None
    for line in RAD.open(encoding="ascii"):
        if line.startswith("START_OBS_MARS"):
            mars = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("START_OBS_UTC") and mars:
            pairs.append((parse_doy_utc(line.split("=", 1)[1].strip().strip('"')), mars))
    diffs = []
    for utc, stamp in pairs:
        h, m, s = (int(v) for v in stamp.split()[1].split(":"))
        rad_s = h * 3600 + m * 60 + s
        ours = lmst_hours(utc, MSL_LMST_LON) * 3600.0
        diffs.append(((ours - rad_s + 43200) % 86400) - 43200)
    noon = int(np.argmax(el[:1600]))
    noon_utc = datetime.fromtimestamp(t[noon], timezone.utc)
    eva_start = datetime(2024, 5, 20, 3, 30, tzinfo=timezone.utc)
    sunset = datetime.fromtimestamp(next_sunset(t, el, eva_start.timestamp()), timezone.utc)
    checks = [
        {"check": "LMST vs RAD START_OBS_MARS (sol 4190, all observations)", "n": len(diffs),
         "mean_s": float(np.mean(diffs)), "max_abs_s": float(np.max(np.abs(diffs))),
         "pass": bool(float(np.max(np.abs(diffs))) < 90.0)},
        {"check": "noon: maximum elevation near LMST 12:00 with the Sun due north or south",
         "elevation_deg": float(el[noon]), "azimuth_deg": float(az[noon]),
         "lmst": format_hours(lmst_hours(noon_utc, SITE["lon_east_deg"])),
         "pass": bool(abs(lmst_hours(noon_utc, SITE["lon_east_deg"]) - 12.0) < 0.75
                      and min(abs(az[noon] - 180), abs(az[noon] % 360)) < 5)},
        {"check": "sunset after the S1 EVA start", "utc": sunset.isoformat(),
         "lmst": format_hours(lmst_hours(sunset, SITE["lon_east_deg"])),
         "pass": bool(17.5 < lmst_hours(sunset, SITE["lon_east_deg"]) < 18.75)},
    ]
    report = {"schema": "redline.t6_spice_verification.v1", "table": str(TABLE.relative_to(ROOT)),
              "sidecar": meta, "checks": checks, "all_pass": all(c["pass"] for c in checks)}
    (ROOT / "docs/verification/T6_SPICE.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"], {k: v for k, v in c.items() if k not in ("check", "pass")})
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
