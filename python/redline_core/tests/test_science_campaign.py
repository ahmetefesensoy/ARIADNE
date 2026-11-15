"""Science campaign config (proje.md §9.2 B1–B10): every station sits on a DERIVED terrain target of
the class its role claims, every task names a frozen action and an existing 3D asset, and every
purpose is written in Turkish and English."""
import json
from pathlib import Path

import pytest

from redline_core.science_campaign import ACTIONS, load_campaign

REPO = Path(__file__).resolve().parents[3]

TARGETS = {"site_id": "TST", "targets": [
    {"target_id": "TST-T01", "science_class": "ridge", "cell": [10, 20], "xy_m": [82.0, 42.0]},
    {"target_id": "TST-T02", "science_class": "hollow", "cell": [30, 5], "xy_m": [22.0, 122.0]}]}


def write(tmp_path, campaign: str):
    (tmp_path / "targets.json").write_text(json.dumps(TARGETS))
    (tmp_path / "assets" / "tool_apxs").mkdir(parents=True)
    path = tmp_path / "campaign.yaml"
    path.write_text(campaign)
    return path


GOOD = """schema: redline.science_campaign.v1
provenance_status: SCENARIO
site_id: TST
question: {tr: "Örüntü sürüyor mu?", en: "Does the pattern continue?"}
mission_brief: {tr: "Amaç", en: "Goal"}
tasks:
  B1_APXS:
    spec: "proje.md §9.2 B1"
    action: ContactScience
    actor: rover_1
    asset: assets/tool_apxs
    data: {status: DERIVED, note: "APXS precision fit"}
    duration_min: 30
    purpose: {tr: "Kimya", en: "Chemistry"}
stations:
  - id: ST-1
    target_id: TST-T01
    expected_class: ridge
    role: control
    name: {tr: "Sırt", en: "Ridge"}
    purpose: {tr: "Kontrol", en: "Control"}
    tasks: [B1_APXS]
"""


def test_a_valid_campaign_resolves_station_positions_from_the_terrain_targets(tmp_path):
    campaign = load_campaign(write(tmp_path, GOOD), tmp_path / "targets.json", root=tmp_path)
    (station,) = campaign.stations
    assert station.xy_m == (82.0, 42.0) and station.science_class == "ridge"
    assert campaign.tasks["B1_APXS"].action == "ContactScience" and "ContactScience" in ACTIONS
    assert campaign.mission_brief["en"] == "Goal"


@pytest.mark.parametrize("change, message", [
    (("expected_class: ridge", "expected_class: hollow"), "class"),
    (("target_id: TST-T01", "target_id: TST-T99"), "unknown target"),
    (("tasks: [B1_APXS]", "tasks: [B9_NOPE]"), "unknown task"),
    (("action: ContactScience", "action: Teleport"), "action"),
    (("asset: assets/tool_apxs", "asset: assets/tool_missing"), "asset"),
    (('purpose: {tr: "Kimya", en: "Chemistry"}', 'purpose: {tr: "Kimya"}'), "en"),
    (("role: control", "role: decoration"), "role"),
    (("provenance_status: SCENARIO", "provenance_status: ARCHIVE"), "SCENARIO"),
])
def test_inconsistent_campaigns_are_refused(tmp_path, change, message):
    with pytest.raises(ValueError, match=message):
        load_campaign(write(tmp_path, GOOD.replace(*change)), tmp_path / "targets.json", root=tmp_path)


def test_the_bxw_campaign_covers_the_spec_surface_tasks_with_an_east_control_and_a_west_test():
    campaign = load_campaign(REPO / "config" / "science_campaign_BXW.yaml",
                             REPO / "data" / "derived" / "BXW" / "planning" / "targets_v1.json", root=REPO)
    used = {campaign.tasks[t].spec.split()[-1] for s in campaign.stations for t in s.tasks}
    assert {"B1", "B2", "B3", "B4", "B5", "B6", "B7", "B10"} <= used
    roles = {s.role for s in campaign.stations}
    assert {"control", "test"} <= roles
    tested = [s for s in campaign.stations if s.role == "test"]
    assert tested and all(s.xy_m[0] < 0 for s in tested)  # the question is about the west extension
    assert {s.science_class for s in tested if s.science_class} == {"ridge", "hollow"}
