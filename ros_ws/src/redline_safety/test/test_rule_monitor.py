"""rule_monitor over real DDS: FR-04 compliance and violation on PET, FR-01 crossings, FR-12 at dusk."""
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock

from redline_core.grid import Grid
from redline_core.planning import save_planning_grid
from redline_msgs.msg import Alert, CrewState, DoseRate, MarginField, MissionState, RedLine, RuleViolation
from redline_safety.rule_monitor import EVENT_QOS, MAP_QOS, STATE_QOS, VIOLATION_TOPIC, RuleMonitorNode

RULES = """provenance_status: SCENARIO
rules:
  FR-01: {evaluated: true, severity: WARNING}
  FR-04: {evaluated: true, window_s: 30.0, severity: EMERGENCY}
"""
RULES_FR12 = RULES + "  FR-12: {evaluated: true, t_dusk_min: 30.0, shelter_radius_m: 10.0, severity: WARNING}\n"
# SIMULATED test inputs: flat 20×20 grid at 4 m, habitat request (0, 0) → cell (10, 10), centre (2, 2).
EVA = """provenance_status: SCENARIO
site_id: TST
crew_ids: [EV1, EV2]
habitat: {requested_xy_m: [0.0, 0.0], placement: nearest_in_largest_component}
reserve: {o2_kg: 0.1, co2_capacity_kg: 0.0, water_kg: 0.0, battery_wh: 0.0}
start: {minutes_above_reserve: 60.0}
lines: {terminate_threshold_min: 10.0, simplify_tolerance_m: 4.0, min_hole_area_m2: 0.0}
tile: {lo_min: -60.0, hi_min: 60.0, bit_depth: 8}
sigma_fallback_percentile: 95.0
"""
HABITAT = (2.0, 2.0)


def shelter_inputs(directory: Path, sun=True, ridge=False) -> dict[str, str]:
    """Grid + configs for the habitat; sun table with sunset 02:00Z and a scenario starting 01:00Z,
    so the FR-12 budget is 1800 − PET seconds (dusk limit at PET 1800 s)."""
    shape = (20, 20)
    z = np.zeros(shape)
    if ridge:
        z[:, 12] = 5.0  # a 5 m wall in the column centred at x = 10 m
    layers = {"z_m": z, "slope_deg": np.zeros(shape), "slope_sigma_deg": np.full(shape, 0.5),
              "relief_m": np.zeros(shape), "wall_slope_deg": np.zeros(shape)}
    save_planning_grid(directory / "grid", Grid((-40.0, -40.0), 4.0, shape[1], shape[0], layers),
                       {"status": "SIMULATED", "site_id": "TST", "note": "synthetic flat test grid"})
    (directory / "suit.yaml").write_text("provenance_status: SCENARIO\nwalk: {}\nsuit: {}\n")
    (directory / "eva.yaml").write_text(EVA)
    params = {"planning_grid": str(directory / "grid.npz"), "suit_file": str(directory / "suit.yaml"),
              "eva_file": str(directory / "eva.yaml")}
    if sun:
        start = datetime(2024, 5, 20, 0, 0, tzinfo=timezone.utc)
        rows = ["utc,sun_az_deg,sun_el_deg,earth_light_time_s"]
        rows += [f"{start + timedelta(minutes=k):%Y-%m-%dT%H:%M:%SZ},270.0000,{30.0 - 0.25 * k:.4f},950.000"
                 for k in range(181)]
        table = directory / "sun.csv"
        table.write_text("\n".join(rows) + "\n", encoding="utf-8")
        (directory / "sun.json").write_text(json.dumps({"site": {"lon_east_deg": 137.37},
                                                        "csv_sha256": hashlib.sha256(table.read_bytes()).hexdigest()}))
        (directory / "s.yaml").write_text("id: T\nsite: TST\nseed: 1\ntime_scale: 1\n"
                                          "start: {historical_utc: '2024-05-20T01:00:00Z', pet_min: 0}\n"
                                          "crew: [EV1, EV2]\n")
        params.update(sun_table=str(table), scenario_file=str(directory / "s.yaml"))
    return params


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


class Rig:
    def __init__(self, tmp_path: Path, rules: str = RULES, params: dict | None = None):
        (tmp_path / "rules.yaml").write_text(rules)
        overrides = {"rules_file": str(tmp_path / "rules.yaml"), **(params or {})}
        self.node = RuleMonitorNode(parameter_overrides=[Parameter(k, value=v) for k, v in overrides.items()])
        self.probe = rclpy.create_node("probe")
        self.clock = self.probe.create_publisher(Clock, "/redline/mission/clock", STATE_QOS)
        self.dose = self.probe.create_publisher(DoseRate, "/env/dose_rate", STATE_QOS)
        self.state = self.probe.create_publisher(MissionState, "/redline/mission/state", MAP_QOS)
        self.redline = self.probe.create_publisher(RedLine, "/redline/redline", MAP_QOS)
        self.crew = {c: self.probe.create_publisher(CrewState, f"/crew/{c}/state", STATE_QOS) for c in ("EV1", "EV2")}
        self.events = []
        self.probe.create_subscription(RuleViolation, VIOLATION_TOPIC, self.events.append, EVENT_QOS)
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)
        self.spin(1.0)

    def spin(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.02)

    def at(self, crew_id, xy, frame="map"):
        message = CrewState()
        message.header.frame_id, message.crew_id = frame, crew_id
        message.pose.pose.position.x, message.pose.pose.position.y = xy
        self.crew[crew_id].publish(message)

    def tick(self, pet, alert, phase, margin=10.0, limiting=MarginField.LIM_O2, limiting_crew="EV1"):
        c = Clock()
        c.clock.sec, c.clock.nanosec = int(pet), int((pet - int(pet)) * 1e9)
        self.clock.publish(c)
        d = DoseRate()
        d.alert = alert
        self.dose.publish(d)
        s = MissionState()
        s.phase = phase
        self.state.publish(s)
        r = RedLine()
        r.margin_now_min, r.limiting_consumable, r.limiting_crew_id = margin, limiting, limiting_crew
        self.redline.publish(r)
        self.spin(0.35)

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def test_shelter_mode_in_time_is_recorded_as_compliance(ros, tmp_path):
    rig = Rig(tmp_path)
    try:
        rig.tick(100.0, False, MissionState.TRAVERSE)
        rig.tick(110.0, True, MissionState.TRAVERSE)
        rig.tick(120.0, True, MissionState.CONTINGENCY)
        rig.spin(0.5)
        fr04 = [e for e in rig.events if e.rule_id == "FR-04"]
        assert len(fr04) == 1 and fr04[0].severity == Alert.INFO
        assert 0.0 <= fr04[0].value <= 10.0 + 1e-6 and fr04[0].threshold == 30.0
        assert rig.node.counts["violations"] == 0
    finally:
        rig.close()


def test_missing_shelter_mode_violates_fr04_and_negative_margin_violates_fr01(ros, tmp_path):
    rig = Rig(tmp_path)
    try:
        rig.tick(0.0, True, MissionState.TRAVERSE)
        rig.tick(20.0, True, MissionState.TRAVERSE)
        rig.tick(40.0, True, MissionState.TRAVERSE, margin=-2.0)
        rig.spin(0.5)
        severities = {(e.rule_id, e.severity) for e in rig.events}
        assert ("FR-04", Alert.EMERGENCY) in severities and ("FR-01", Alert.WARNING) in severities
        assert rig.node.counts["violations"] == 2
    finally:
        rig.close()


def fr(rig, rule):
    return [e for e in rig.events if e.rule_id == rule]


def test_fr12_flags_crew_outside_at_the_dusk_limit_and_clears_when_back(ros, tmp_path):
    rig = Rig(tmp_path, RULES_FR12, shelter_inputs(tmp_path))
    try:
        assert rig.node.fr12_status == "evaluated" and rig.node.habitat_xy == HABITAT
        rig.at("EV1", HABITAT)
        rig.at("EV2", (30.0, 2.0))  # 28 m out
        rig.spin(0.3)
        rig.tick(1000.0, False, MissionState.TRAVERSE)
        assert not fr(rig, "FR-12") and rig.node.daylight_budget_s == pytest.approx(800.0)
        rig.tick(1900.0, False, MissionState.TRAVERSE)  # 100 s past the dusk limit
        rig.spin(0.3)
        (violation,) = fr(rig, "FR-12")
        assert violation.severity == Alert.WARNING and "EV2" in violation.text and "EV1" not in violation.text
        assert violation.value == pytest.approx(100.0 / 60.0, rel=1e-5) and violation.threshold == 30.0
        rig.at("EV2", (9.0, 2.0))  # 7 m from the habitat: inside the 10 m radius
        rig.spin(0.3)
        rig.tick(2000.0, False, MissionState.TRAVERSE)
        rig.spin(0.3)
        assert [e.severity for e in fr(rig, "FR-12")] == [Alert.WARNING, Alert.INFO]
        assert "back in shelter" in fr(rig, "FR-12")[-1].text
    finally:
        rig.close()


def test_fr12_satisfied_in_shelter_and_fr01_skips_margins_that_no_longer_bind(ros, tmp_path):
    rig = Rig(tmp_path, RULES_FR12, shelter_inputs(tmp_path))
    try:
        rig.at("EV1", HABITAT)
        rig.at("EV2", (2.0, 8.0))
        rig.spin(0.3)
        rig.tick(1900.0, False, MissionState.TRAVERSE, margin=-1.7, limiting=MarginField.LIM_DAYLIGHT)
        rig.spin(0.3)
        (record,) = fr(rig, "FR-12")
        assert record.severity == Alert.INFO and "all crew in shelter" in record.text
        assert not fr(rig, "FR-01") and rig.node.counts["fr12_satisfied"] == 1  # dusk margin at home
        # A consumable shortfall at home during the EVA is still FR-01 ...
        rig.tick(1910.0, False, MissionState.TRAVERSE, margin=-2.0, limiting=MarginField.LIM_O2)
        rig.spin(0.3)
        # ... and stops binding once the EVA is over (DEBRIEF) with the crew inside.
        rig.tick(1920.0, False, MissionState.DEBRIEF, margin=-2.5, limiting=MarginField.LIM_O2)
        rig.spin(0.3)
        shortfall, cleared = fr(rig, "FR-01")
        assert shortfall.severity == Alert.WARNING and "limit: O2" in shortfall.text
        assert cleared.severity == Alert.INFO and cleared.text == "EV1 in shelter"
        assert rig.node.counts["violations"] == 1
    finally:
        rig.close()


def test_fr12_counts_a_crew_member_without_a_position_as_outside(ros, tmp_path):
    rig = Rig(tmp_path, RULES_FR12, shelter_inputs(tmp_path))
    try:
        rig.at("EV1", HABITAT)
        rig.at("EV2", (40.0, 40.0), frame="odom")  # rejected: not the map frame
        rig.spin(0.3)
        rig.tick(1801.0, False, MissionState.TRAVERSE)
        rig.spin(0.3)
        (violation,) = fr(rig, "FR-12")
        assert "EV2 (no position)" in violation.text and rig.node.counts["rejected_states"] == 1
    finally:
        rig.close()


def test_fr12_without_a_sun_table_is_reported_not_configured(ros, tmp_path):
    rig = Rig(tmp_path, RULES_FR12, shelter_inputs(tmp_path, sun=False))
    try:
        assert rig.node.fr12 is None and "sun_table" in rig.node.fr12_status
        assert rig.node.habitat_xy == HABITAT  # FR-01's in-shelter check still knows the habitat
    finally:
        rig.close()


RULES_FR05 = RULES + ("  FR-05: {evaluated: true, max_distance_m: 100.0, grace_s: 60.0, eye_height_m: 2.0, "
                      "hysteresis_m: 0.5, severity: WARNING}\n")


def test_fr05_caution_when_apart_then_warning_after_the_grace_then_cleared(ros, tmp_path):
    rig = Rig(tmp_path, RULES_FR05, shelter_inputs(tmp_path, sun=False))
    try:
        rig.at("EV1", (-36.0, -36.0))
        rig.at("EV2", (36.0, 36.0))  # 102 m apart
        rig.spin(0.3)
        rig.tick(10.0, False, MissionState.TRAVERSE)
        rig.tick(50.0, False, MissionState.TRAVERSE)
        rig.tick(75.0, False, MissionState.TRAVERSE)
        rig.at("EV2", (-20.0, -36.0))
        rig.spin(0.3)
        rig.tick(80.0, False, MissionState.TRAVERSE)
        rig.spin(0.3)
        assert [(e.severity, round(e.value)) for e in fr(rig, "FR-05")] == [
            (Alert.CAUTION, 102), (Alert.WARNING, 102), (Alert.INFO, 16)]
        assert "EV1" in fr(rig, "FR-05")[0].text and "EV2" in fr(rig, "FR-05")[0].text
    finally:
        rig.close()


def test_fr05_flags_a_buddy_hidden_behind_a_ridge(ros, tmp_path):
    rig = Rig(tmp_path, RULES_FR05, shelter_inputs(tmp_path, sun=False, ridge=True))
    try:
        rig.at("EV1", (2.0, 2.0))
        rig.at("EV2", (22.0, 2.0))  # 20 m apart, 5 m wall between, eyes at 2 m
        rig.spin(0.3)
        rig.tick(10.0, False, MissionState.TRAVERSE)
        rig.spin(0.3)
        (caution,) = fr(rig, "FR-05")
        assert caution.severity == Alert.CAUTION and "line of sight" in caution.text
    finally:
        rig.close()


def test_fr05_does_not_apply_to_a_single_crew_member(ros, tmp_path):
    inputs = shelter_inputs(tmp_path, sun=False)
    rig = Rig(tmp_path, RULES_FR05, {**inputs, "crew_ids": ["EV1"]})
    try:
        assert rig.node.fr05 == {} and "single" in rig.node.fr05_status
    finally:
        rig.close()


# --- S2 (proje.md §8.7, §16): suit leak detected from telemetry ---------------------------------------
RULES_LEAK = RULES + ("  SUIT_LEAK: {evaluated: true, factor_on: 1.5, factor_off: 1.2, hold_s: 30.0, "
                      "severity: WARNING}\n")


def leak_state(rig, crew_id, factor, metabolic_w=300.0):
    """CrewState whose O2 rate is `factor` times what the metabolic model expects (default suit)."""
    from redline_core.redline import Rates
    from redline_core.params import load_models

    suit = load_models(rig.suit_file)[1]
    message = CrewState()
    message.header.frame_id, message.crew_id = "map", crew_id
    message.pose.pose.position.x, message.pose.pose.position.y = HABITAT
    message.consumables.metabolic_w = metabolic_w
    message.consumables.o2_rate_kg_h = factor * Rates.from_metabolic_power(metabolic_w, suit).o2_kg_s * 3600.0
    rig.crew[crew_id].publish(message)


def test_a_suit_leak_is_detected_from_telemetry_after_the_hold_and_cleared(ros, tmp_path):
    inputs = shelter_inputs(tmp_path, sun=False)
    rig = Rig(tmp_path, RULES_LEAK, inputs)
    rig.suit_file = inputs["suit_file"]
    alerts = []
    rig.probe.create_subscription(Alert, "/redline/alerts", alerts.append, EVENT_QOS)
    try:
        for pet in (10.0, 30.0, 45.0):
            leak_state(rig, "EV1", 1.0)
            leak_state(rig, "EV2", 3.0)
            rig.spin(0.2)
            rig.tick(pet, False, MissionState.TRAVERSE)
        rig.spin(0.3)
        (detected,) = fr(rig, "SUIT_LEAK")
        assert detected.severity == Alert.WARNING and "EV2" in detected.text
        assert detected.value == pytest.approx(3.0, rel=1e-3) and detected.threshold == pytest.approx(1.5)
        (alert,) = [a for a in alerts if a.code == "SUIT_LEAK"]
        assert alert.severity == Alert.WARNING and list(alert.related_ids) == ["EV2"]
        leak_state(rig, "EV2", 1.0)
        rig.spin(0.2)
        rig.tick(50.0, False, MissionState.TRAVERSE)
        rig.spin(0.3)
        assert [e.severity for e in fr(rig, "SUIT_LEAK")] == [Alert.WARNING, Alert.INFO]
    finally:
        rig.close()


def test_suit_leak_is_not_evaluated_unless_the_rules_file_enables_it(ros, tmp_path):
    rig = Rig(tmp_path, RULES, shelter_inputs(tmp_path, sun=False))
    try:
        assert rig.node.leak == {} and "not evaluated" in rig.node.leak_status
    finally:
        rig.close()
