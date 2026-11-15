"""VOI on the real BXW plan: candidate count, time per candidate, effect per obstacle density (D015).

Builds the SCIENCE plan from the T2 v2 planning grid and the derived targets (as planner_server
does), then evaluates every VOI candidate for each SCENARIO obstacle density λ_f (per km²).
Reports, per density: candidate count, median/p95 ms, how many candidates have VOI > 0, the top
five and whether they lie on the planned walks. Writes a JSON report. Run in the REDLINE venv.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.orienteering import Candidate, RoutePlanner
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid
from redline_core.science_value import load_science
from redline_core.voi import VoiEstimator

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--densities", default="0,10,100,1000", help="obstacle features per km²")
    parser.add_argument("--max-duration-min", type=float, default=300.0)
    parser.add_argument("--out", default="test-results/bench_voi_bxw.json")
    args = parser.parse_args()
    grid, meta = load_planning_grid(ROOT / "data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    walk, suit = load_models(ROOT / "config/suit.yaml")
    crew = load_crew(ROOT / "config/crew.yaml")
    eva = load_eva(ROOT / "config/eva.yaml")
    model = ReturnFieldModel(grid, walk, suit, crew, eva)
    science = load_science(ROOT / "config/science_BXW.yaml")
    targets = json.loads((ROOT / "data/derived/BXW/planning/targets_v1.json").read_text(encoding="utf-8"))
    if targets["planning_grid"]["npz_sha256"] != meta["npz_sha256"]:
        raise SystemExit("targets were derived on a different planning grid")
    candidates = [Candidate(t["target_id"], tuple(t["cell"]), t["science_class"], 60.0 * float(t["service_min"]),
                            tuple(t["tasks"])) for t in targets["targets"]]
    member = crew[eva.crew_ids[0]]
    planner = RoutePlanner(model.terrain, model.field, model.habitat_cell, candidates, science, science.prior,
                           member, suit, walk, model.start_resources(member.crew_id), model.reserve,
                           60.0 * args.max_duration_min, z=eva.z_eps, sigma_theta=eva.sigma_theta)
    started = time.perf_counter()
    route = planner.heuristic("SCIENCE")
    plan_s = time.perf_counter() - started
    if not route.order:
        raise SystemExit("no valid SCIENCE route")
    report = {"schema": "redline.bench_voi.v1", "status": "SCENARIO", "planning_grid_sha256": meta["npz_sha256"],
              "plan": {"order": [planner.candidates[i].target_id for i in route.order],
                       "min_margin_min": route.min_margin_s / 60.0, "heuristic_s": plan_s}, "densities": []}
    for density in (float(v) for v in args.densities.split(",")):
        est = VoiEstimator(model, planner, route, obstacle_density_per_km2=density)
        on_path = {c for p in est.paths for c in p.cells}
        cells = est.candidate_cells()
        est.evaluate(cells[0])  # numba warm-up
        results = [est.evaluate(c) for c in cells]
        ms = np.array([r.compute_ms for r in results])
        results.sort(key=lambda r: r.score, reverse=True)
        row = {"obstacle_density_per_km2": density, "candidates": len(cells),
               "median_ms": float(np.median(ms)), "p95_ms": float(np.percentile(ms, 95)),
               "total_s": float(ms.sum() / 1000.0), "positive_voi": int(sum(r.voi_s > 0 for r in results)),
               "negative_voi": int(sum(r.voi_s < 0 for r in results)),
               "top5": [{"cell": list(r.cell), "on_path": r.cell in on_path, "p_block": 1.0 - r.p_open,
                         "voi_min": r.voi_s / 60.0, "legacy_voi_min": r.legacy_voi_s / 60.0,
                         "score": r.score} for r in results[:5]]}
        report["densities"].append(row)
        print(json.dumps({k: row[k] for k in ("obstacle_density_per_km2", "candidates", "median_ms", "p95_ms",
                                              "positive_voi", "negative_voi")}))
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
