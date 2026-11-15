"""Derive BXW SCENARIO science targets from terrain (D011).

Ridges/hollows = strongest topographic position index extrema (1 m Gale DEM, annulus
5-25 m, averaged to 4 m cells) among cells that are walkable, workable (|μ|+1.645σ ≤ 15°),
within the risk-adjusted return reach of the habitat and ≥ 50 m from it. Six per class,
≥ 100 m apart (12 = the exact-search limit of orienteering). Writes an immutable JSON next
to the planning grid. Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.grid import block_reduce, north_up_to_grid
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid
from redline_core.targets import pick_targets, topographic_position_index

ROOT = Path(__file__).resolve().parents[1]
DEM = "data/derived/BXW/dem_enu.tif"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--planning-grid", default="data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    parser.add_argument("--reach-min", type=float, default=120.0)
    parser.add_argument("--per-class", type=int, default=6)
    parser.add_argument("--spacing-m", type=float, default=100.0)
    parser.add_argument("--service-min", type=float, default=20.0)
    parser.add_argument("--out", default="data/derived/BXW/planning/targets_v1.json")
    args = parser.parse_args()
    out = ROOT / args.out
    if out.exists():
        raise SystemExit(f"{out} exists; target sets are immutable records")

    grid, meta = load_planning_grid(ROOT / args.planning_grid)
    walk, suit = load_models(ROOT / "config/suit.yaml")
    eva = load_eva(ROOT / "config/eva.yaml")
    model = ReturnFieldModel(grid, walk, suit, load_crew(ROOT / "config/crew.yaml"), eva)
    with rasterio.open(ROOT / DEM) as src:
        z1 = north_up_to_grid(src.read(1, masked=True).astype(float).filled(np.nan))
    tpi = block_reduce(topographic_position_index(z1, 1.0, 5.0, 25.0), 4, "mean")
    slope, sigma = grid.layers["slope_deg"], grid.layers["slope_sigma_deg"]
    w_eps = model.field.time_eps_s(eva.z_eps, eva.sigma_theta)
    hy, hx = model.habitat_cell
    yy, xx = np.mgrid[0:grid.height, 0:grid.width]
    eligible = (~model.terrain.banned_mask & np.isfinite(sigma)
                & (np.abs(slope) + 1.645 * np.nan_to_num(sigma, nan=np.inf) <= 15.0)
                & (w_eps <= args.reach_min * 60.0)
                & (np.hypot(yy - hy, xx - hx) * grid.resolution_m >= 50.0))
    targets = pick_targets(tpi, eligible, grid.resolution_m, per_class=args.per_class,
                           min_spacing_m=args.spacing_m, min_abs_tpi_m=0.3, prefix="BXW-T")
    record = {
        "schema": "redline.targets.v1", "status": "SCENARIO", "site_id": "BXW",
        "note": "terrain-derived candidate stations; composition is not observed",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "planning_grid": {"path": args.planning_grid, "npz_sha256": meta["npz_sha256"]},
        "dem": {"path": DEM, "sha256": hashlib.sha256((ROOT / DEM).read_bytes()).hexdigest()},
        "rules": {"tpi_annulus_m": [5.0, 25.0], "reach_min": args.reach_min, "workable_slope_deg": 15.0,
                  "min_from_habitat_m": 50.0, "spacing_m": args.spacing_m, "per_class": args.per_class,
                  "min_abs_tpi_m": 0.3},
        "habitat_cell": list(model.habitat_cell), "eligible_cells": int(eligible.sum()),
        "targets": [{"target_id": t.target_id, "science_class": t.science_class, "cell": list(t.cell),
                     "xy_m": list(grid.cell_center(*t.cell)), "tpi_m": round(t.tpi_m, 3),
                     "return_eps_min": round(float(w_eps[t.cell] / 60.0), 2),
                     "service_min": args.service_min, "tasks": ["PHOTO", "LIBS", "APXS"]} for t in targets],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(record, indent=1) + "\n")
    for t in record["targets"]:
        print(t["target_id"], t["science_class"], t["xy_m"], t["tpi_m"], t["return_eps_min"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
