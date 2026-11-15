"""Summarise a captured nominal-scenario rosbridge feed against the scenario's expectations (D015).

Receipt times are mapped to PET with the mission-clock messages in the same feed. Reports phases,
DecisionRecords, plan versions, rule records (and which `expected` rules held), the limiting crew
and consumable, the tightest margin_now, and whether the run reached DEBRIEF.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import json
from pathlib import Path

import yaml

PHASES = {0: "BRIEFING", 1: "PRECURSOR", 2: "TRAVERSE", 3: "STATION_SCIENCE", 4: "RETURN", 5: "CONTINGENCY",
          6: "DEBRIEF"}
LIMITS = {0: "O2", 1: "CO2", 2: "WATER", 3: "BATTERY", 4: "DAYLIGHT", 5: "SHELTER", 255: "NONE"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("feed", type=Path)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    scenario = yaml.safe_load(args.scenario.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in args.feed.open(encoding="utf-8")]
    clock = [(r["_redline_elapsed_sec"], r["msg"]["clock"]["sec"] + r["msg"]["clock"]["nanosec"] * 1e-9)
             for r in rows if r["topic"] == "/redline/mission/clock"]
    clock_t = [c[0] for c in clock]

    def pet_at(t):
        i = bisect.bisect_right(clock_t, t) - 1
        return clock[i][1] if i >= 0 else 0.0

    phases, decisions, plans, rules, limiting, margins = [], [], {}, [], collections.Counter(), []
    last = None
    for r in rows:
        topic, msg, pet = r["topic"], r["msg"], pet_at(r["_redline_elapsed_sec"])
        if topic == "/redline/mission/state" and msg["phase"] != last:
            last = msg["phase"]
            phases.append({"pet_s": pet, "phase": PHASES.get(last, last), "plan": msg["active_plan_id"]})
        elif topic == "/redline/decisions":
            decisions.append({"pet_s": pet, "id": msg["decision_id"], "context": msg["context"],
                              "evidence_ids": msg["evidence_ids"]})
        elif topic == "/redline/plan":
            plans[msg["plan_id"]] = {"version": msg["version"], "stations": [s["target_id"] for s in msg["stations"]],
                                     "total_duration_min": msg["total_duration_min"]}
        elif topic == "/safety/violations":
            rules.append({"pet_s": pet, "rule": msg["rule_id"], "severity": msg["severity"], "value": msg["value"],
                          "text": msg["text"]})
        elif topic == "/redline/redline" and msg["limiting_crew_id"]:
            limiting[(msg["limiting_crew_id"], LIMITS.get(msg["limiting_consumable"], msg["limiting_consumable"]))] += 1
            if msg["margin_now_min"] is not None:
                margins.append((pet, msg["margin_now_min"]))
    above_info = [r for r in rules if r["severity"] > 0]
    expected = []
    for item in scenario.get("expected") or []:
        fired = [r for r in above_info if r["rule"] == item["rule"]]
        holds = not fired
        expected.append({"rule": item["rule"], "must_hold": item["must_hold"], "held": holds,
                         "ok": holds == bool(item["must_hold"]), "records": len(fired)})
    summary = {
        "schema": "redline.scenario_feed_summary.v1", "scenario": scenario["id"], "seed": scenario["seed"],
        "feed": str(args.feed), "phases": phases, "decisions": decisions, "plans": plans,
        "rule_records": rules, "violations_above_info": len(above_info), "expected": expected,
        "all_expected_ok": all(e["ok"] for e in expected),
        "limiting_counts": {f"{c}/{lim}": n for (c, lim), n in limiting.most_common()},
        "margin_now_min_min": min((m for _, m in margins), default=None),
        "debrief_reached": any(p["phase"] == "DEBRIEF" for p in phases),
        "last_pet_s": clock[-1][1] if clock else None,
    }
    args.out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: summary[k] for k in ("scenario", "phases", "plans", "violations_above_info", "expected",
                                              "all_expected_ok", "limiting_counts", "margin_now_min_min",
                                              "debrief_reached", "last_pet_s")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
