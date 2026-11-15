"""Hidden SCENARIO truth for S4 and its counterfactual (spec scenario_rocks_<seed>.json; D015).

The scenario author fixes the obstacle before any VOI runs: a 10 m boulder-cluster disc on the
first leg of the S0/S4 plan v1, about 50 m from the habitat. Plan v1 is computed exactly as
planner_server does (same inputs, Pareto SCIENCE route, value floor 0.7, 300 min); the leg path
is the walking model's shortest path. No random rocks: the causal story is one obstacle. Writes
scenario_rocks_4.json (obstacle) and scenario_rocks_4c.json (same, no obstacle) under
data/derived/BXW/scenario/ and prints where the obstacle is. Run in the REDLINE venv.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.orienteering import Candidate, RoutePlanner
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid
from redline_core.science_value import load_science
from redline_core.truth import Obstacle, scenario_world, write_truth
from redline_core.walkback import leg_path

ROOT = Path(__file__).resolve().parents[1]
DISTANCE_M, RADIUS_M = 50.0, 10.0


def main() -> int:
    grid, meta = load_planning_grid(ROOT / "data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    walk, suit = load_models(ROOT / "config/suit.yaml")
    crew = load_crew(ROOT / "config/crew.yaml")
    eva = replace(load_eva(ROOT / "config/eva.yaml"), crew_ids=("EV1", "EV2"))
    model = ReturnFieldModel(grid, walk, suit, crew, eva)
    science = load_science(ROOT / "config/science_BXW.yaml")
    targets = json.loads((ROOT / "data/derived/BXW/planning/targets_v1.json").read_text(encoding="utf-8"))
    candidates = [Candidate(t["target_id"], tuple(t["cell"]), t["science_class"], 60.0 * float(t["service_min"]),
                            tuple(t["tasks"])) for t in targets["targets"]]
    planning_crew = max(eva.crew_ids, key=lambda c: model.nominal_rates(c).o2_kg_s)
    planner = RoutePlanner(model.terrain, model.field, model.habitat_cell, candidates, science, science.prior,
                           model.crew[planning_crew], suit, walk, model.start_resources(planning_crew), model.reserve,
                           60.0 * 300.0, z=eva.z_eps, sigma_theta=eva.sigma_theta, value_floor_fraction=0.7)
    route = planner.pareto()["SCIENCE"]["route"]
    first = planner.candidates[route.order[0]]
    cells = leg_path(model.terrain, model.habitat_cell, tuple(first.cell))
    xy = np.array([grid.cell_center(*c) for c in cells])
    along = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
    k = int(np.searchsorted(along, DISTANCE_M))
    ox, oy = (float(v) for v in xy[k])
    out = ROOT / "data/derived/BXW/scenario"
    note = (f"S4 author-placed obstacle (fixed before VOI): {RADIUS_M:g} m disc {along[k]:.0f} m along the first leg "
            f"(habitat → {first.target_id}) of plan v1 {[planner.candidates[i].target_id for i in route.order]}")
    world = scenario_world(grid, "BXW", seed=4, k=0.0, d_range_m=(0.3, 3.0),
                           obstacles=[Obstacle("S4-BOULDERS", ox, oy, RADIUS_M)], note=note)
    counter = scenario_world(grid, "BXW", seed=4, k=0.0, d_range_m=(0.3, 3.0),
                             note="S4 counterfactual: no obstacle (same scenario otherwise)")
    write_truth(world, out / "scenario_rocks_4.json")
    write_truth(counter, out / "scenario_rocks_4c.json")
    print(json.dumps({"plan_v1": [planner.candidates[i].target_id for i in route.order], "first_leg_cells": len(cells),
                      "obstacle_xy": [ox, oy], "radius_m": RADIUS_M, "along_m": float(along[k]),
                      "planning_grid_sha256": meta["npz_sha256"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
