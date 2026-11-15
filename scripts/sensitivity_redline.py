"""Which assumptions move the storm red line most? One-at-a-time sensitivity on the real BXW grid (T12 subset).

Metric: storm-mode safe area, km2 = walkable cells whose risk-adjusted walk back to the habitat
(T_eps = mu + z*sqrt(var + (sigma_theta*mu)^2), proje.md §7.5) is within the solar-storm warning
limit (FR-03). Each parameter is moved to a low and a high value while all others stay at their
config values. This is a local sensitivity check, not a Monte Carlo or a validation against field data.
Status: DERIVED (real terrain) from SCENARIO parameters. Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (parameter, where, base-config key, low, high, why these bounds)
VARIANTS = [
    ("sep_limit_min", "rule", None, 15.0, 30.0, "warning-time limit; 20 min in D012, Löwe+2025 report >=30 min warnings"),
    ("z_eps", "eva", "z_eps", 1.282, 2.326, "risk quantile 90% / 99% instead of 95%"),
    ("sigma_theta", "eva", "sigma_theta", 0.1, 0.3, "relative model-time uncertainty"),
    ("tobler_peak_kmh", "walk", "tobler_peak_kmh", 5.0, 7.0, "Earth-equivalent peak walking speed +/-1 km/h"),
    ("speed_factor_unobserved", "walk", "speed_factor_unobserved", 0.6, 0.85,
     "how much slower a crew walks over terrain no robot has seen"),
    ("slope_max_deg", "walk", "slope_max_deg", 20.0, 30.0, "suited slope ban"),
]


def tornado(base: float, rows: list[dict]) -> list[dict]:
    """Signed change from the base for each parameter, largest total swing first."""
    bars = []
    for row in rows:
        lo, hi = row["metric_low"], row["metric_high"]
        if not (math.isfinite(lo) and math.isfinite(hi)):
            raise ValueError(f"non-finite metric for {row['parameter']}")
        bars.append({**row, "delta_low": lo - base, "delta_high": hi - base, "swing": abs(hi - lo)})
    return sorted(bars, key=lambda b: b["swing"], reverse=True)


def main() -> int:
    import numpy as np

    from redline_core.field_model import ReturnFieldModel, load_eva
    from redline_core.params import load_crew, load_models
    from redline_core.planning import load_planning_grid

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grid", default="data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    parser.add_argument("--sep-limit-min", type=float, default=20.0)
    parser.add_argument("--report", default="docs/verification/SENSITIVITY.json")
    args = parser.parse_args()
    grid, meta = load_planning_grid(ROOT / args.grid)
    walk, suit = load_models(ROOT / "config/suit.yaml")
    eva = load_eva(ROOT / "config/eva.yaml")
    crew = load_crew(ROOT / "config/crew.yaml")
    cell_km2 = grid.resolution_m ** 2 / 1e6

    def area(field, z, sigma, limit_min) -> float:
        t = field.time_eps_s(z, sigma)
        return round(float((np.isfinite(t) & (t <= limit_min * 60)).sum() * cell_km2), 4)

    base_model = ReturnFieldModel(grid, walk, suit, crew, eva)
    base = area(base_model.field, eva.z_eps, eva.sigma_theta, args.sep_limit_min)
    rows = []
    for name, where, key, low, high, why in VARIANTS:
        metric = {}
        for side, value in (("low", low), ("high", high)):
            z, sigma, limit, field = eva.z_eps, eva.sigma_theta, args.sep_limit_min, base_model.field
            if where == "rule":
                limit = value
            elif key == "z_eps":
                z = value
            elif key == "sigma_theta":
                sigma = value
            else:
                field = ReturnFieldModel(grid, dataclasses.replace(walk, **{key: value}), suit, crew, eva).field
            metric[side] = area(field, z, sigma, limit)
        base_value = args.sep_limit_min if where == "rule" else getattr(eva if where == "eva" else walk, key)
        rows.append({"parameter": name, "base": base_value, "low": low, "high": high, "why": why,
                     "metric_low": metric["low"], "metric_high": metric["high"]})
        print(name, metric)
    report = {"check": "one-at-a-time sensitivity of the storm-mode safe-return area (T12 subset)",
              "status": "DERIVED terrain, SCENARIO parameters; local sensitivity, not validation",
              "metric": f"km2 of walkable cells with T_eps <= sep limit (base {args.sep_limit_min:g} min)",
              "grid": args.grid, "grid_sha256": meta.get("npz_sha256"),
              "habitat_xy_m": [round(v, 1) for v in base_model.habitat_xy],
              "base_km2": base, "bars": tornado(base, rows)}
    out = ROOT / args.report
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("base", base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
