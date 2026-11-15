"""SIMULATED EV1 test walk for the T5 BXW run: habitat → a cell with the requested
return time, following the return field's own time-optimal path (next_hop) in
reverse, so every waypoint is walkable under the planning rules. Not a plan.
Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--planning-grid", default="data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    parser.add_argument("--eva", default="config/eva.yaml")
    parser.add_argument("--return-min", type=float, default=8.0, help="target mean return time (minutes)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    grid, meta = load_planning_grid(ROOT / args.planning_grid)
    walk, suit = load_models(ROOT / "config/suit.yaml")
    model = ReturnFieldModel(grid, walk, suit, load_crew(ROOT / "config/crew.yaml"), load_eva(ROOT / args.eva))
    time_s = model.field.time_s
    finite = np.isfinite(time_s)
    target = np.unravel_index(np.argmin(np.where(finite, np.abs(time_s - args.return_min * 60.0), np.inf)),
                              time_s.shape)
    chain, flat = [], int(target[0] * grid.width + target[1])
    while flat >= 0:
        chain.append(divmod(flat, grid.width))
        flat = int(model.field.next_hop.flat[flat])
    chain.reverse()  # habitat first
    if chain[0] != model.habitat_cell:
        raise SystemExit("next_hop chain does not end at the habitat")
    waypoints = [list(grid.cell_center(iy, ix)) for iy, ix in chain]
    report = {
        "schema": "redline.t5.walk_path.v1", "status": "SIMULATED",
        "note": "test motion along the return field's optimal path, reversed; not a mission plan",
        "planning_grid_sha256": meta["npz_sha256"], "habitat_cell": model.habitat_cell,
        "target_cell": [int(target[0]), int(target[1])], "target_return_min": float(time_s[target] / 60.0),
        "cells": len(chain), "waypoints_xy_m": waypoints,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("habitat_cell", "target_cell", "target_return_min", "cells")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
