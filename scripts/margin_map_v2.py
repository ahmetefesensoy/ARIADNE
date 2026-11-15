"""BXW margin map v2 and before/after summary for the D010 model decisions.

Uses the live model (redline_core.field_model) on the v2 planning grid with config/eva.yaml
and config/suit.yaml. Writes data/derived/BXW/margin-v2-<UTC>/ with a PNG (state after
`--pet-h` hours of nominal walking from the design-point start) and a JSON that also
reports the T2-comparable snapshot (reserve + 40 min of nominal use). SCENARIO product.
Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t2_margin_map import plot, signed_area_m2, summary_stats  # noqa: E402

from redline_core.cost_human import metabolic_power, standing_power_w, station_power_w, walking_speed  # noqa: E402
from redline_core.field_model import CrewInput, ReturnFieldModel, load_eva  # noqa: E402
from redline_core.params import load_crew, load_models  # noqa: E402
from redline_core.planning import load_planning_grid  # noqa: E402
from redline_core.redline import Resources  # noqa: E402
from redline_core.suit_state import deplete  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rings(items):
    areas = [signed_area_m2(r) for r in items]
    return {"rings": len(items), "net_area_km2": sum(areas) / 1e6}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--planning-grid", default="data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    parser.add_argument("--pet-h", type=float, default=4.0)
    args = parser.parse_args()

    grid, meta = load_planning_grid(ROOT / args.planning_grid)
    walk, suit = load_models(ROOT / "config/suit.yaml")
    crew = load_crew(ROOT / "config/crew.yaml")
    eva = load_eva(ROOT / "config/eva.yaml")
    model = ReturnFieldModel(grid, walk, suit, crew, eva)
    ev1 = crew["EV1"]
    nominal_speed = walk.speed_factor_unobserved * walking_speed(0.0, walk)
    powers = {
        "standing_w": standing_power_w(ev1, walk),
        "station_w": station_power_w(ev1, suit, walk),
        "walk_nominal_w": metabolic_power(nominal_speed, 0.0, walk.eta_default, ev1, suit, walk),
        "walk_flat_detected_w": metabolic_power(walking_speed(0.0, walk), 0.0, walk.eta_default, ev1, suit, walk),
        "design_w": eva.design_metabolic_w,
        "nominal_speed_m_s": nominal_speed,
    }
    rates = model.nominal_rates("EV1")
    start = model.start_resources("EV1")
    reserve = model.reserve
    endurance_h = {}
    for name, value, rate in (("o2", start.o2_kg - reserve.o2_kg, rates.o2_kg_s),
                              ("co2", start.co2_capacity_kg - reserve.co2_capacity_kg, rates.co2_kg_s),
                              ("water", start.water_kg - reserve.water_kg, rates.water_kg_s),
                              ("battery", start.battery_wh - reserve.battery_wh, rates.battery_w / 3600.0)):
        endurance_h[name] = value / rate / 3600.0

    later = deplete(start, rates, args.pet_h * 3600.0)
    snap = model.snapshot({"EV1": CrewInput(later, rates, None)})
    # T2-comparable: reserve + 40 min nominal (T2 used no time-based reserve).
    t2_eva = replace(eva, start_basis="nominal_minutes", start_minutes_above_reserve=40.0, reserve_minutes=0.0)
    t2_start = Resources(0.1 + rates.o2_kg_s * 2400, rates.co2_kg_s * 2400, rates.water_kg_s * 2400,
                         rates.battery_w * 2400 / 3600)
    compare = ReturnFieldModel(grid, walk, suit, crew, t2_eva).snapshot({"EV1": CrewInput(t2_start, rates, None)})

    field_min = model.field.time_eps_s(eva.z_eps, eva.sigma_theta) / 60.0
    unreachable = ~np.isfinite(model.field.time_s)
    out = ROOT / "data/derived/BXW" / f"margin-v2-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    out.mkdir(parents=True, exist_ok=False)
    png = out / "margin_map_BXW_EV1_v2.png"
    margin_min = snap.combined.field.margin_min
    caption = (f"v2 (D010): eğim/σ iki DTM işlemesinin topluluğundan; giysi maliyeti hızla orantılı (EWT 3/8 g); "
               f"giysi tasarım noktası 8 sa × 351,7 W, 30 dk rezerv; habitat seçimle ({model.habitat_xy[0]:.0f}, "
               f"{model.habitat_xy[1]:.0f}) m. Durum: {args.pet_h:g} sa nominal yürüyüş tüketiminden sonra. "
               "SCENARIO, plan değildir.")
    title = (f"BXW · margin haritası v2 — EVA'nın {args.pet_h:g}. saatinde dönüş payı (SCENARIO, plan değildir)")
    abort = [r[:, :2] for r in snap.abort_rings]
    terminate = [r[:, :2] for r in snap.terminate_rings]
    x0, y0 = grid.origin_xy
    plot(png, (x0, x0 + grid.width * grid.resolution_m, y0, y0 + grid.height * grid.resolution_m), field_min,
         margin_min, model.terrain.banned_mask | unreachable, model.habitat_xy, abort, terminate, caption,
         title=title)
    summary = {
        "schema": "redline.margin_map_v2.v1", "provenance_status": "SCENARIO",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "planning_grid": {"path": args.planning_grid, "npz_sha256": meta["npz_sha256"]},
        "configs": {p: sha256(ROOT / p) for p in ("config/eva.yaml", "config/suit.yaml", "config/crew.yaml")},
        "habitat": {"cell": model.habitat_cell, "xy_m": model.habitat_xy, **model.habitat_report},
        "banned_fraction": float(model.terrain.banned_mask.mean()),
        "reachable_fraction": float(np.isfinite(model.field.time_s).mean()),
        "w_eps_min": summary_stats(field_min),
        "powers_ev1": powers,
        "start": start.__dict__, "reserve": reserve.__dict__,
        "endurance_h_at_nominal_walking": endurance_h,
        "after_pet": {"pet_h": args.pet_h, "remaining": later.__dict__,
                      "safe_fraction": float(np.mean(np.nan_to_num(snap.combined.field.margin_s, nan=-np.inf) >= 0)),
                      "margin_at_habitat_min": float(margin_min[model.habitat_cell]),
                      "abort": rings(abort), "terminate": rings(terminate)},
        "t2_comparable_40min": {
            "safe_fraction": float(np.mean(np.nan_to_num(compare.combined.field.margin_s, nan=-np.inf) >= 0)),
            "abort": rings([r[:, :2] for r in compare.abort_rings])},
        "png": {"path": str(png.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(png)},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("habitat", "banned_fraction", "reachable_fraction", "powers_ev1",
                                              "endurance_h_at_nominal_walking", "after_pet",
                                              "t2_comparable_40min")}, indent=1, default=float))
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
