"""Scenario loader and replay mapping (proje.md §16; D012)."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from redline_core.clocks import MissionTime
from redline_core.scenario import load_scenario

REPO = Path(__file__).resolve().parents[3]
S1 = REPO / "config" / "scenarios" / "S1_SEP_4190.yaml"


def test_s1_loads_and_maps_pet_to_the_real_alarm_time():
    s1 = load_scenario(S1)
    assert s1.scenario_id == "S1_SEP_4190" and s1.rad_sols == (4189, 4190, 4191) and s1.rad_detector == "E"
    alarm = s1.replay_mapping().historical_utc(MissionTime(111 * 60 + 50))
    assert alarm == datetime(2024, 5, 20, 5, 21, 50, tzinfo=timezone.utc)
    assert s1.run_id(datetime(2026, 11, 14, 12, 0, 0, tzinfo=timezone.utc)) == "20261114T120000Z-S1_SEP_4190-42"


def test_rejects_unknown_keys_and_bad_detector(tmp_path):
    text = S1.read_text(encoding="utf-8")
    (tmp_path / "a.yaml").write_text(text + "\nsurprise: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown"):
        load_scenario(tmp_path / "a.yaml")
    (tmp_path / "b.yaml").write_text(text.replace("detector: E", "detector: X"), encoding="utf-8")
    with pytest.raises(ValueError, match="detector"):
        load_scenario(tmp_path / "b.yaml")


# --- D015: canonical event payload and the T7/T9 scenario keys ------------------------------
from redline_core.scenario import EVENT_SCHEMA, ScenarioEvent, encode_event, parse_event  # noqa: E402


def test_event_payload_round_trips_and_plain_text_has_none():
    event = ScenarioEvent(45.0, "SUIT_LEAK", {"crew_id": "EV2", "k_leak": 3.0})
    text = encode_event(event, "scenario event at PET 45 min")
    assert text.startswith("scenario event at PET 45 min | ")
    assert parse_event(text) == event
    assert parse_event("SCENARIO_START: S1 started") is None


@pytest.mark.parametrize("text", ["x | {not json", 'x | {"schema": "other", "type": "A", "t_min": 1, "params": {}}',
                                  'x | {"schema": "%s", "type": "", "t_min": 1, "params": {}}' % EVENT_SCHEMA])
def test_event_payload_rejects_malformed_text(text):
    with pytest.raises(ValueError):
        parse_event(text)


BASE = """id: T
site: TST
seed: 3
start: {historical_utc: '2024-05-20T00:00:00Z'}
crew: [EV1, EV2]
"""


def test_new_keys_load_with_defaults_that_keep_s1_unchanged(tmp_path):
    path = tmp_path / "s.yaml"
    path.write_text(BASE)
    plain = load_scenario(path)
    assert plain.initial_phase == "TRAVERSE" and plain.truth_file == "" and plain.plan == {}
    path.write_text(BASE + "initial_phase: BRIEFING\ntruth_file: data/x/scenario_rocks_3.json\n"
                    "plan: {objective: SCIENCE, max_duration_min: 300}\nprecursor: {vehicle_id: scout_1}\n")
    loaded = load_scenario(path)
    assert loaded.initial_phase == "BRIEFING" and loaded.truth_file.endswith("scenario_rocks_3.json")
    assert loaded.plan["objective"] == "SCIENCE" and loaded.precursor["vehicle_id"] == "scout_1"
    path.write_text(BASE + "initial_phase: LUNCH\n")
    with pytest.raises(ValueError, match="initial_phase"):
        load_scenario(path)


def test_crew_trail_s_is_a_per_crew_mapping_of_known_crew(tmp_path):
    path = tmp_path / "s.yaml"
    path.write_text(BASE + "crew_trail_s: {EV2: 240}\n")
    assert load_scenario(path).crew_trail_s == {"EV2": 240.0}
    path.write_text(BASE + "crew_trail_s: {EV3: 10}\n")
    with pytest.raises(ValueError, match="crew_trail_s"):
        load_scenario(path)


# --- Council 2026-11-15: a short playable chapter around the real sol 4190 alarm -------------------
C1 = REPO / "config" / "scenarios" / "C1_SOL4190_CHAPTER.yaml"
T6_RAD = REPO / "docs" / "verification" / "T6_RAD.json"


def test_c1_chapter_puts_the_real_alarm_a_few_minutes_into_play_at_real_time():
    import json

    c1 = load_scenario(C1)
    assert c1.time_scale == 1.0  # D015: Unreal moves EV1, so mission time runs at x1
    assert c1.crew == ("EV1",) and c1.rad_sols == (4189, 4190, 4191) and c1.rad_detector == "E"
    check = next(c for c in json.loads(T6_RAD.read_text(encoding="utf-8"))["checks"] if "alarm" in c["check"])
    alarm = datetime.fromisoformat(check["observed_utc"])  # ARCHIVE RAD E series, not shifted
    play_s = (alarm - c1.historical_utc).total_seconds()
    assert 10 * 60 <= play_s <= 13 * 60
    assert c1.replay_mapping().historical_utc(MissionTime(c1.pet0_s + play_s)) == alarm
