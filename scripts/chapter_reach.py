"""Where does the red line bind in a short playable chapter? (council 2026-11-15; proje.md §7.5–7.7, §12 FR-03)

On the real BXW planning grid, computes the risk-adjusted walk back to the habitat (T_ε, the time the
SEP rule FR-03 compares with its 20 min limit) for the campaign targets in config/targets_BXW.yaml and
the planning targets, plus the walkable area inside each T_ε band. Analysis only: it changes no
config. The walk is the conservative planning model (D010); the player's sprint (SCENARIO cap) is
reported separately as a real-time estimate, not as a physiology claim. Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid

ROOT = Path(__file__).resolve().parents[1]
BANDS_MIN = (5.0, 10.0, 15.0, 20.0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grid", default="data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    parser.add_argument("--report", default="docs/verification/CHAPTER_REACH.json")
    parser.add_argument("--sep-limit-min", type=float, default=20.0)
    args = parser.parse_args()
    grid, meta = load_planning_grid(ROOT / args.grid)
    walk, suit = load_models(ROOT / "config/suit.yaml")
    eva = load_eva(ROOT / "config/eva.yaml")
    model = ReturnFieldModel(grid, walk, suit, load_crew(ROOT / "config/crew.yaml"), eva)
    field = model.field
    t_eps = field.time_eps_s(eva.z_eps, eva.sigma_theta)
    sprint = yaml.safe_load((ROOT / "config/gameplay_preview.yaml").read_text(encoding="utf-8"))["sprint_cap_m_s"]
    hx, hy = model.habitat_xy

    def at(name: str, xy, source: str) -> dict:
        cell = model.cell_of((float(xy[0]), float(xy[1])))  # campaign points carry z as a third value
        if cell is None:
            return {"id": name, "source": source, "xy_m": list(xy), "error": "outside grid"}
        mu, eps, path_m = (float(a[cell]) for a in (field.time_s, t_eps, field.distance_m))
        return {"id": name, "source": source, "xy_m": [round(float(v), 1) for v in xy[:2]],
                "straight_m": round(math.hypot(xy[0] - hx, xy[1] - hy), 1),
                "path_m": round(path_m, 1) if math.isfinite(path_m) else None,
                "walk_mu_min": round(mu / 60, 2) if math.isfinite(mu) else None,
                "t_eps_min": round(eps / 60, 2) if math.isfinite(eps) else None,
                "sep_fr03_binds": bool(math.isfinite(eps) and eps / 60 > args.sep_limit_min),
                "fr03_slack_min": round(args.sep_limit_min - eps / 60, 2) if math.isfinite(eps) else None,
                "sprint_real_min": round(path_m / sprint / 60, 2) if math.isfinite(path_m) else None}

    points = []
    campaign = yaml.safe_load((ROOT / "config/targets_BXW.yaml").read_text(encoding="utf-8"))
    for t in campaign.get("targets", []):
        points.append(at(t["id"], t["point_m"], "config/targets_BXW.yaml (campaign, SCENARIO)"))
    planning = json.loads((ROOT / "data/derived/BXW/planning/targets_v1.json").read_text(encoding="utf-8"))
    r, (x0, y0) = grid.resolution_m, grid.origin_xy
    for t in planning["targets"]:
        iy, ix = t["cell"]
        points.append(at(t["target_id"], (x0 + (ix + 0.5) * r, y0 + (iy + 0.5) * r),
                         "data/derived/BXW/planning/targets_v1.json (planning, DERIVED TPI)"))
    finite = np.isfinite(t_eps)
    cell_km2 = r * r / 1e6
    bands = {f"t_eps<={b:g}min_km2": round(float((t_eps[finite] <= b * 60).sum() * cell_km2), 3) for b in BANDS_MIN}
    ring = finite & (t_eps >= 12 * 60) & (t_eps <= 18 * 60)
    ys, xs = np.nonzero(ring)
    straight = np.hypot(x0 + (xs + 0.5) * r - hx, y0 + (ys + 0.5) * r - hy)
    report = {"check": "red-line binding distance for a short chapter (FR-03 SEP shelter limit)",
              "status": "DERIVED (real BXW grid, conservative planning walk); sprint is SCENARIO",
              "grid": args.grid, "grid_sha256": meta.get("npz_sha256"), "habitat_xy_m": [round(hx, 1), round(hy, 1)],
              "sep_limit_min": args.sep_limit_min, "z_eps": eva.z_eps, "sigma_theta": eva.sigma_theta,
              "sprint_cap_m_s": sprint, "walkable_area_by_t_eps": bands,
              "ring_12_18_min": {"cells": int(ring.sum()), "straight_m_p10_p50_p90":
                                 [round(float(np.percentile(straight, q)), 1) for q in (10, 50, 90)] if ring.any()
                                 else None},
              "points": points}
    out = ROOT / args.report
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in points:
        print(p)
    print(bands, report["ring_12_18_min"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
