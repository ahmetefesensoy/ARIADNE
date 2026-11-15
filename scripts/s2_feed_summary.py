"""S2 acceptance from a captured feed (proje.md §16 S2, §17: limiting = O2 and EV2; D015, D018 follow-up).

Reports the leak event, its telemetry detection (SUIT_LEAK rule record), the phase response, the
limiting crew/consumable before the leak and after detection, and an independent re-computation of
EV2's O2 return margin from the recorded telemetry with redline_core on the real grid:

    margin_O2 = (o2_kg − reserve_o2 − k · need_o2(cell)) / o2_rate        (k = reported/metabolic O2)

compared with the published margin_now while EV2/O2 is limiting. The acceptance uses samples where
EV2's telemetry was steady (two consecutive states within 0.5 m and with the same O2 rate): while
walking at 60x, or at the ingress step where the rate drops, the CrewState that
walkback_field used cannot be paired exactly from the feed, so moving samples are reported only as
median / p95. Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import bisect
import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import yaml

from redline_core.field_model import ReturnFieldModel, leak_factor, load_eva
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {0: "O2", 1: "CO2", 2: "WATER", 3: "BATTERY", 4: "DAYLIGHT", 5: "SHELTER"}
PHASES = {0: "BRIEFING", 1: "PRECURSOR", 2: "TRAVERSE", 3: "STATION_SCIENCE", 4: "RETURN", 5: "CONTINGENCY",
          6: "DEBRIEF"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("feed", type=Path)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--grid", default="data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    parser.add_argument("--crew", default="EV2")
    parser.add_argument("--tolerance-min", type=float, default=1.0)
    args = parser.parse_args()
    scenario = yaml.safe_load(args.scenario.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in args.feed.open(encoding="utf-8")]
    clock = [(r["_redline_elapsed_sec"], r["msg"]["clock"]["sec"] + r["msg"]["clock"]["nanosec"] * 1e-9)
             for r in rows if r["topic"] == "/redline/mission/clock"]
    clock_t = [c[0] for c in clock]

    def pet_at(t):
        i = bisect.bisect_right(clock_t, t) - 1
        return clock[i][1] if i >= 0 else 0.0

    leak_min = next(e["t_min"] for e in scenario["events"] if e["type"] == "SUIT_LEAK")
    grid, meta = load_planning_grid(ROOT / args.grid)
    walk, suit = load_models(ROOT / "config/suit.yaml")
    # The launch hands the scenario crew to every node (D015); eva.yaml lists the default crew only.
    eva = dataclasses.replace(load_eva(ROOT / "config/eva.yaml"), crew_ids=tuple(scenario["crew"]))
    model = ReturnFieldModel(grid, walk, suit, load_crew(ROOT / "config/crew.yaml"), eva)
    need = model.field.consumables(model.crew[args.crew], suit, walk, risk=True, z=eva.z_eps,
                                   sigma_theta=eva.sigma_theta).o2_kg
    reserve = model.reserve.o2_kg

    detection, phases, before, after, checks, last_state, ratios = None, [], {}, {}, [], None, []
    prev_xy, prev_rate, still = None, None, False
    phase = None
    for r in rows:
        topic, msg, pet = r["topic"], r["msg"], pet_at(r["_redline_elapsed_sec"])
        if topic == "/safety/violations" and msg["rule_id"] == "SUIT_LEAK" and msg["severity"] > 0 and not detection:
            detection = {"pet_s": pet, "factor": msg["value"], "text": msg["text"]}
        elif topic == "/redline/mission/state" and msg["phase"] != phase:
            phase = msg["phase"]
            phases.append({"pet_s": round(pet, 1), "phase": PHASES.get(phase, phase)})
        elif topic == f"/crew/{args.crew}/state":
            p = msg["pose"]["pose"]["position"]
            rate = msg["consumables"]["o2_rate_kg_h"]
            still = (prev_xy is not None and math.hypot(p["x"] - prev_xy[0], p["y"] - prev_xy[1]) <= 0.5
                     and prev_rate is not None and abs(rate - prev_rate) <= 1e-6 * max(abs(rate), 1e-9))
            prev_xy, prev_rate, last_state = (p["x"], p["y"]), rate, msg
            c = msg["consumables"]
            if c["o2_rate_kg_h"] and c["metabolic_w"]:
                ratios.append((pet, leak_factor(c["o2_rate_kg_h"] / 3600.0, c["metabolic_w"], suit)))
        elif topic == "/redline/redline" and msg["limiting_crew_id"]:
            key = f"{msg['limiting_crew_id']}/{LIMITS.get(msg['limiting_consumable'], msg['limiting_consumable'])}"
            if pet < 60 * leak_min:
                before[key] = before.get(key, 0) + 1
            elif detection:
                after[key] = after.get(key, 0) + 1
                if key == f"{args.crew}/O2" and last_state and msg["margin_now_min"] is not None:
                    c, p = last_state["consumables"], last_state["pose"]["pose"]["position"]
                    cell = model.cell_of((p["x"], p["y"]))
                    k = leak_factor(c["o2_rate_kg_h"] / 3600.0, c["metabolic_w"], suit)
                    hand = (c["o2_kg"] - reserve - k * float(need[cell])) / (c["o2_rate_kg_h"] / 3600.0) / 60.0
                    checks.append({"pet_s": round(pet, 1), "published_min": msg["margin_now_min"],
                                   "hand_min": hand, "o2_kg": c["o2_kg"], "reserve_o2_kg": reserve,
                                   "k_leak": k, "need_o2_kg": float(need[cell]),
                                   "o2_rate_kg_h": c["o2_rate_kg_h"], "cell": list(cell), "still": still})
    diffs = [abs(c["published_min"] - c["hand_min"]) for c in checks]
    still_diffs = [abs(c["published_min"] - c["hand_min"]) for c in checks if c["still"]]
    pre = [f for t, f in ratios if t < 60 * leak_min]
    post = [f for t, f in ratios if t >= 60 * leak_min + 60]
    after_total = sum(after.values())
    report = {
        "schema": "redline.s2_acceptance.v1", "scenario": scenario["id"], "feed": str(args.feed),
        "grid_sha256": meta.get("npz_sha256"), "leak_event_pet_s": 60 * leak_min,
        "telemetry_ratio_before_median": float(np.median(pre)) if pre else None,
        "telemetry_ratio_after_median": float(np.median(post)) if post else None,
        "detection": detection,
        "detection_delay_s": round(detection["pet_s"] - 60 * leak_min, 1) if detection else None,
        "phases": phases, "limiting_before_leak": before, "limiting_after_detection": after,
        "limiting_after_detection_is_crew_o2": bool(after_total) and after.get(f"{args.crew}/O2", 0) == after_total,
        "margin_checks": len(checks), "margin_max_abs_diff_min": max(diffs) if diffs else None,
        "margin_median_abs_diff_min": float(np.median(diffs)) if diffs else None,
        "margin_p95_abs_diff_min": float(np.percentile(diffs, 95)) if diffs else None,
        "worst": checks[int(np.argmax(diffs))] if diffs else None,
        "still_checks": len(still_diffs), "still_max_abs_diff_min": max(still_diffs) if still_diffs else None,
        "margin_within_tolerance": bool(still_diffs) and max(still_diffs) <= args.tolerance_min,
        "tolerance_min": args.tolerance_min,
        "sample": checks[len(checks) // 2] if checks else None,
        "min_published_margin_after_detection_min": min((c["published_min"] for c in checks), default=None),
    }
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
