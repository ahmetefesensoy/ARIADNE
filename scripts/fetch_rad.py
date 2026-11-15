"""Fetch MSL RAD RDR sols, write ARCHIVE dose tables and verify sol 4190 (proje.md §6.3; D012).

Downloads into data/raw/env/rad/ (each file in that directory only), writes
data/env/rad_<sol>.csv + .json, and checks the spec's [D] values for sol 4190 with the
redline_core SEP rule. Writes docs/verification/T6_RAD.json. Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from redline_core.sep import background_median
from redline_data.rad import read_rad_table, sha256_file, write_rad_table

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/DATA/SOL_04134_04257/"
FILES = {4189: "RAD_RDR_2024_139_17_46_4189_V00", 4190: "RAD_RDR_2024_140_18_30_4190_V00",
         4191: "RAD_RDR_2024_141_19_08_4191_V00"}
# proje.md §6.3 [D]: sol 4190 E series (observation -> µGy/h, UTC) and the E maximum.
EXPECTED_E = {76: (5.72, "05:04:45"), 78: (9.97, "05:21:50"), 80: (85.38, "05:38:56"), 82: (214.04, None),
              84: (316.37, None), 86: (343.28, None), 88: (351.42427, "06:15:19")}


def fetch(url: str, path: Path) -> None:
    if path.exists():
        return
    request = urllib.request.Request(url, headers={"User-Agent": "redline-research-client"})
    tmp = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(request, timeout=600) as response, tmp.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    tmp.rename(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", default="docs/verification/T6_RAD.json")
    args = parser.parse_args()
    raw, env = ROOT / "data/raw/env/rad", ROOT / "data/env"
    raw.mkdir(parents=True, exist_ok=True)
    tables = {}
    for sol, stem in FILES.items():
        for ext in (".LBL", ".TXT"):
            fetch(BASE + stem + ext, raw / (stem + ext))
        out = env / f"rad_{sol}.csv"
        if not out.exists():
            write_rad_table(raw / (stem + ".TXT"), out, label=raw / (stem + ".LBL"), source_url=BASE + stem + ".TXT")
        tables[sol] = read_rad_table(out)

    readings = tables[4190]
    by_obs = {r.observation: r for r in readings}
    checks = []
    for obs, (value, clock) in EXPECTED_E.items():
        r = by_obs.get(obs)
        ok = r is not None and abs(r.dose_e_ugy_h - value) <= 0.005 and (clock is None or r.utc.strftime("%H:%M:%S") == clock)
        checks.append({"check": f"sol 4190 obs {obs} E", "expected": value, "expected_utc": clock,
                       "observed": None if r is None else r.dose_e_ugy_h,
                       "observed_utc": None if r is None else r.utc.isoformat(), "pass": bool(ok)})
    e = [(r.utc.timestamp(), r.dose_e_ugy_h) for r in readings if r.dose_e_ugy_h is not None]
    peak = max(e, key=lambda v: v[1])
    checks.append({"check": "sol 4190 E maximum", "expected": 351.42427, "observed": peak[1],
                   "observed_utc": datetime.fromtimestamp(peak[0], timezone.utc).isoformat(),
                   "pass": abs(peak[1] - 351.42427) < 1e-6})
    # %25 alarm on E with a 6 h median background, readings across sols 4189-4191.
    series = sorted((r.utc.timestamp(), r.dose_e_ugy_h) for sol in tables for r in tables[sol]
                    if r.dose_e_ugy_h is not None)
    t = np.array([s[0] for s in series]); d = np.array([s[1] for s in series])
    first_alarm = None
    for k in range(len(t)):
        background = background_median(t, d, t[k])
        if np.isfinite(background) and d[k] >= 1.25 * background:
            first_alarm = (t[k], d[k], background)
            break
    alarm_utc = datetime.fromtimestamp(first_alarm[0], timezone.utc) if first_alarm else None
    checks.append({"check": "first 25% E alarm (6 h median background)", "expected_utc": "2024-05-20T05:21:50+00:00",
                   "expected_background": 5.6, "observed_utc": alarm_utc.isoformat() if alarm_utc else None,
                   "observed_background": first_alarm[2] if first_alarm else None,
                   "pass": bool(alarm_utc and alarm_utc.strftime("%H:%M:%S") == "05:21:50"
                                and abs(first_alarm[2] - 5.6) < 0.3)})
    counts = {"observation_sections_4190": None, "dose_blocks_4190": len(readings)}
    report = {
        "schema": "redline.t6_rad_verification.v1", "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "ARCHIVE data, DERIVED checks",
        "tables": {sol: {"csv": f"data/env/rad_{sol}.csv",
                         "sidecar": json.loads((env / f"rad_{sol}.json").read_text(encoding="utf-8"))}
                   for sol in tables},
        "counts": counts,
        "spec_count_note": "proje.md §6.3 says 186 observation sections / 93 dose blocks for sol 4190; "
                           "the PDS V00 file (created 2024-310) has 258 / 129 (see VERIFICATION_LOG)",
        "checks": checks, "all_pass": all(c["pass"] for c in checks),
    }
    path = ROOT / args.report
    path.write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"], c.get("observed"), c.get("observed_utc"))
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
