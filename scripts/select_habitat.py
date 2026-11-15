"""Select the BXW SCENARIO habitat site with redline_core.siting (D010).

Pad: MSL landing-site engineering limits (≤ 15° at 2–5 m with z·σ, ≤ 5° over 200 m) on a
20 × 20 m pad; reach: walkable area with risk-adjusted return ≤ the budget. Writes an
immutable selection report next to the planning grid. Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from redline_core.cost_human import prepare_terrain
from redline_core.params import load_models
from redline_core.planning import load_planning_grid
from redline_core.siting import SitingRules, select_habitat

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--planning-grid", default="data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    parser.add_argument("--suit", default="config/suit.yaml")
    parser.add_argument("--request-xy", type=float, nargs=2, default=(0.0, 0.0),
                        help="site centre of the BXW science area (sites.yaml origin)")
    parser.add_argument("--reach-budget-min", type=float, default=60.0)
    parser.add_argument("--search-radius-m", type=float, default=600.0)
    parser.add_argument("--lattice-m", type=float, default=12.0)
    parser.add_argument("--sigma-fallback-percentile", type=float, default=95.0)
    parser.add_argument("--out", default="data/derived/BXW/planning/habitat_selection_v1.json")
    args = parser.parse_args()

    out = ROOT / args.out
    if out.exists():
        raise SystemExit(f"{out} exists; selections are immutable records")
    grid, meta = load_planning_grid(ROOT / args.planning_grid)
    walk, _ = load_models(ROOT / args.suit)
    sigma = grid.layers["slope_sigma_deg"]
    fallback = float(np.nanpercentile(sigma, args.sigma_fallback_percentile))
    terrain = prepare_terrain(grid, walk, sigma_fallback_deg=fallback)
    rules = SitingRules(search_radius_m=args.search_radius_m, lattice_m=args.lattice_m,
                        reach_budget_s=args.reach_budget_min * 60.0)
    requested = grid.cell_index(*args.request_xy)
    started = time.perf_counter()
    result = select_habitat(terrain, grid.layers["slope_deg"], sigma, requested, rules)
    elapsed = time.perf_counter() - started
    xy = grid.cell_center(*result.cell)
    report = {
        "schema": "redline.habitat_selection.v1",
        "status": "SCENARIO",
        "note": "chosen site under stated rules; not a mapped or certified landing site",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "planning_grid": {"path": args.planning_grid, "npz_sha256": meta["npz_sha256"]},
        "suit_file": {"path": args.suit, "sha256": sha256(ROOT / args.suit)},
        "rules": asdict(rules),
        "rule_sources": {
            "pad_slopes": "MSL Engineering User Guide v2 (marsoweb.nas.nasa.gov/landingsites/msl/memoranda/"
                          "MSL_Eng_User_Guide_v2.pdf): <=15 deg over 2-5 m, <=5 deg over 200-500 m",
            "reach": "walkable area with risk-adjusted return time <= budget (D010)",
        },
        "request": {"xy_m": list(args.request_xy), "cell": list(requested)},
        "sigma_fallback_deg": fallback,
        "selected": {"cell": list(result.cell), "xy_m": list(xy), "reach_cells": result.reach_cells,
                     "reach_km2": result.reach_cells * grid.resolution_m**2 / 1e6,
                     "distance_from_request_m": float(np.hypot(xy[0] - args.request_xy[0],
                                                               xy[1] - args.request_xy[1]))},
        "pad_cells_total": result.pad_cells_total,
        "candidates_evaluated": result.candidates_evaluated,
        "ranking_top10": result.ranking,
        "elapsed_s": elapsed,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("selected", "pad_cells_total", "candidates_evaluated", "elapsed_s")},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
