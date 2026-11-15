"""Summarise a captured S1 rosbridge feed: alarm PET, phases, FR-04, alerts, line area.

Receipt times are mapped to PET with the mission-clock messages in the same feed.
"""
from __future__ import annotations

import argparse
import bisect
import json
from pathlib import Path

PHASES = {0: "BRIEFING", 1: "PRECURSOR", 2: "TRAVERSE", 3: "STATION_SCIENCE", 4: "RETURN", 5: "CONTINGENCY",
          6: "DEBRIEF"}


def area(points) -> float:
    total = 0.0
    for a, b in zip(points, points[1:] + points[:1]):
        total += a["x"] * b["y"] - b["x"] * a["y"]
    return 0.5 * total


def after_pairs(areas, alarm_pet):
    """(PET, area) more than 30 s (PET) after the alarm, when the SEP line has settled."""
    return [(p, a) for p, a in areas if p is not None and alarm_pet is not None and p > alarm_pet + 30]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("feed", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    clock_t, clock_pet, rows = [], [], []
    with args.feed.open(encoding="utf-8") as handle:
        for line in handle:
            envelope = json.loads(line)
            rows.append(envelope)
            if envelope["topic"] == "/redline/mission/clock":
                clock_t.append(envelope["_redline_elapsed_sec"])
                c = envelope["msg"]["clock"]
                clock_pet.append(c["sec"] + c["nanosec"] * 1e-9)

    def pet_at(t):
        i = bisect.bisect_right(clock_t, t) - 1
        return clock_pet[i] if i >= 0 else None

    alarm_pet, alarm_end, phases, alerts, rules, scenario, areas, margins, env = None, None, [], [], [], [], [], [], []
    last_phase = None
    for r in rows:
        topic, msg, t = r["topic"], r["msg"], r["_redline_elapsed_sec"]
        pet = pet_at(t)
        if topic == "/env/dose_rate" and msg["alert"] and alarm_pet is None:
            alarm_pet = pet
            alarm_dose = {"e": msg["dose_rate_e_ugy_h"], "background_e": msg["background_e_ugy_h"],
                          "historical_utc_sec": msg["historical_utc"]["sec"], "source_sol": msg["source_sol"]}
        elif topic == "/env/dose_rate" and not msg["alert"] and alarm_pet is not None and alarm_end is None:
            alarm_end = pet
        elif topic == "/redline/mission/state" and msg["phase"] != last_phase:
            last_phase = msg["phase"]
            phases.append({"pet_s": pet, "phase": PHASES.get(msg["phase"], msg["phase"])})
        elif topic == "/redline/alerts":
            alerts.append({"pet_s": pet, "code": msg["code"], "severity": msg["severity"], "text": msg["text"]})
        elif topic == "/safety/violations":
            rules.append({"pet_s": pet, "rule": msg["rule_id"], "severity": msg["severity"], "value": msg["value"],
                          "text": msg["text"]})
        elif topic == "/env/state":
            env.append({"pet_s": pet, "sun_el_deg": msg["sun_el_deg"], "sun_az_deg": msg["sun_az_deg"],
                        "lmst": msg["lmst"], "earth_light_time_s": msg["earth_light_time_s"]})
        elif topic == "/redline/scenario/event":
            scenario.append({"pet_s": pet, "code": msg["code"]})
        elif topic == "/redline/redline":
            areas.append((pet, sum(area(p["points"]) for p in msg["abort_regions"]) / 1e6))
            margins.append((pet, msg["margin_now_min"]))
    before = [a for p, a in areas if p is not None and alarm_pet is not None and p < alarm_pet]
    after = [a for _, a in after_pairs(areas, alarm_pet)]
    # SEP effect alone: while the alarm lasts. "after" also holds later limits (battery, dusk).
    during = [a for p, a in after_pairs(areas, alarm_pet) if alarm_end is None or p < alarm_end]
    summary = {
        "schema": "redline.s1_feed_summary.v1", "feed": str(args.feed),
        "alarm_pet_s": alarm_pet, "alarm_end_pet_s": alarm_end, "alarm": alarm_dose if alarm_pet is not None else None,
        "phases": phases, "alerts": alerts, "rule_records": rules, "scenario_events": scenario,
        "abort_area_km2_before_alarm": before[-1] if before else None,
        "abort_area_km2_during_alarm_min": min(during) if during else None,
        "abort_area_km2_after_alarm_min": min(after) if after else None,
        "margin_now_min_last": margins[-1][1] if margins else None,
        "fr04": next((r for r in rules if r["rule"] == "FR-04"), None),
        "fr12": next((r for r in rules if r["rule"] == "FR-12"), None),
        "fr01": [r for r in rules if r["rule"] == "FR-01"],
        "debrief_reached": any(p["phase"] == "DEBRIEF" for p in phases),
        "env_first": env[0] if env else None, "env_last": env[-1] if env else None,
    }
    args.out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("alarm_pet_s", "alarm_end_pet_s", "alarm", "phases", "fr04", "fr12",
                                              "fr01", "abort_area_km2_before_alarm",
                                              "abort_area_km2_during_alarm_min", "abort_area_km2_after_alarm_min",
                                              "debrief_reached", "env_first", "env_last")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
