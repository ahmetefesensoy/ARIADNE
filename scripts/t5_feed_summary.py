"""Summarise a captured T5 rosbridge feed (runs/<run_id>/ue_feed.jsonl).

Reports per-topic counts and frame sizes, the RedLine margin_now series and
polygon sizes, and decodes the FieldTile PNGs with redline_core to check the
grid geometry Unreal will receive. Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import base64
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from redline_core.fieldtile import decode_tile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("feed", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    sizes = defaultdict(list)
    series, tiles, polygons, clock = [], [], [], []
    with args.feed.open(encoding="utf-8") as handle:
        for line in handle:
            envelope = json.loads(line)
            topic, msg, t = envelope["topic"], envelope["msg"], envelope["_redline_elapsed_sec"]
            sizes[topic].append(len(line.encode("utf-8")))
            if topic == "/redline/redline":
                now = msg["margin_now_min"]  # rosbridge sends NaN as null
                series.append({"t_s": round(t, 2), "margin_now_min": None if now is None else round(now, 3),
                               "limiting_crew_id": msg["limiting_crew_id"],
                               "limiting_consumable": msg["limiting_consumable"],
                               "abort_rings": len(msg["abort_regions"]),
                               "terminate_rings": len(msg["terminate_regions"])})
                polygons.append(sum(len(p["points"]) for p in msg["abort_regions"] + msg["terminate_regions"]))
            elif topic == "/redline/tiles/margin_min":
                png = base64.b64decode(msg["png"])
                values = decode_tile(png, msg["scale"], msg["offset"], msg["nodata_byte"])
                tiles.append({"t_s": round(t, 2), "png_bytes": len(png), "shape": list(values.shape),
                              "width": msg["width"], "height": msg["height"], "origin": msg["origin"],
                              "resolution_m": msg["resolution_m"],
                              "safe_cells": int(np.count_nonzero(values >= 0)),
                              "nodata_cells": int(np.count_nonzero(np.isnan(values)))})
            elif topic == "/redline/mission/clock":
                clock.append((t, msg["clock"]["sec"] + msg["clock"]["nanosec"] * 1e-9))

    finite = [s["margin_now_min"] for s in series if s["margin_now_min"] is not None]
    pet_rate = None
    if len(clock) >= 2:
        (t0, p0), (t1, p1) = clock[0], clock[-1]
        pet_rate = (p1 - p0) / (t1 - t0) if t1 > t0 else None
    summary = {
        "schema": "redline.t5.feed_summary.v1",
        "feed": str(args.feed),
        "topics": {t: {"count": len(v), "max_frame_bytes": max(v), "median_frame_bytes": int(np.median(v))}
                   for t, v in sizes.items()},
        "mission_clock_pet_per_wall_s": pet_rate,
        "redline": {
            "count": len(series),
            "null_margin_now": sum(s["margin_now_min"] is None for s in series),
            "margin_now_first_finite": finite[0] if finite else None,
            "margin_now_last_finite": finite[-1] if finite else None,
            "max_polygon_points": max(polygons) if polygons else 0,
            "limiting_crew_ids": sorted({s["limiting_crew_id"] for s in series}),
            "limiting_consumables": sorted({s["limiting_consumable"] for s in series}),
            "series": series,
        },
        "tiles": {"count": len(tiles), "max_png_bytes": max((x["png_bytes"] for x in tiles), default=0),
                  "first": tiles[0] if tiles else None, "last": tiles[-1] if tiles else None},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("topics", "mission_clock_pet_per_wall_s")}, indent=1))
    print(json.dumps({k: v for k, v in summary["redline"].items() if k != "series"}, indent=1))
    print(json.dumps({"tiles": {k: v for k, v in summary["tiles"].items()}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
