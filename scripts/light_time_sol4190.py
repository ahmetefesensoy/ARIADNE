"""Earth-Mars one-way light time at the sol 4190 alarm and peak (DERIVED from NAIF SPICE kernels).

Uses Earth and Mars system barycentres (de440s); the planet-centre difference is far below the
0.01 min shown. Output: docs/verification/LIGHT_TIME_SOL4190.json
"""
import hashlib
import json
import math
from pathlib import Path

import spiceypy as sp

ROOT = Path(__file__).resolve().parents[1]
KERNELS = [ROOT / "data/raw/spice/naif0012.tls", ROOT / "data/raw/spice/de440s.bsp"]
EVENTS = {"alarm_utc": "2024-05-20T05:21:50", "peak_utc": "2024-05-20T06:15:19"}  # T6_RAD.json


def main() -> None:
    for kernel in KERNELS:
        sp.furnsh(str(kernel))
    out = {"schema": "redline.light_time.v1", "status": "DERIVED",
           "method": "spkpos MARS BARYCENTER from EARTH BARYCENTER, J2000, light-time corrected (LT)",
           "kernels": {k.name: hashlib.sha256(k.read_bytes()).hexdigest() for k in KERNELS}, "events": {}}
    for name, utc in EVENTS.items():
        position, light_s = sp.spkpos("MARS BARYCENTER", sp.str2et(utc), "J2000", "LT", "EARTH BARYCENTER")
        out["events"][name] = {"utc": utc + "Z", "one_way_min": round(light_s / 60, 2),
                               "round_trip_min": round(2 * light_s / 60, 2),
                               "distance_au": round(math.dist((0, 0, 0), position) / 1.495978707e8, 3)}
    path = ROOT / "docs/verification/LIGHT_TIME_SOL4190.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out["events"]))


if __name__ == "__main__":
    main()
