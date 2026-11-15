"""walkback_field over real DDS: start state, crew input, cell deltas, daylight, message layout."""
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock

from redline_core.cost_human import DETECTED, metabolic_power, walking_speed
from redline_core.field_model import CrewInput
from redline_core.fieldtile import decode_tile
from redline_core.redline import LIM_DAYLIGHT, LIM_NONE, LIM_O2, Resources
from redline_msgs.msg import CellDelta, CellState, CrewState, FieldTile, MarginField, RedLine
from redline_planner.walkback_field import (
    DELTA_TOPIC,
    EVENT_QOS,
    MAP_QOS,
    REDLINE_TOPIC,
    STATE_QOS,
    WalkbackFieldNode,
    margin_topic,
    tile_topic,
)
from t5_fixtures import HABITAT_XY, ORIGIN, SHAPE, flat_index, reference_model, spin_until, write_inputs


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


class Rig:
    def __init__(self, paths):
        self.node = WalkbackFieldNode(parameter_overrides=[Parameter(k, value=v) for k, v in paths.items()] +
                                      [Parameter("rate_hz", value=10.0)])
        self.probe = rclpy.create_node("probe")
        self.redlines, self.margins, self.tiles, self.crew_tiles = [], [], [], []
        self.probe.create_subscription(RedLine, REDLINE_TOPIC, self.redlines.append, MAP_QOS)
        self.probe.create_subscription(MarginField, margin_topic("EV1"), self.margins.append, MAP_QOS)
        self.probe.create_subscription(FieldTile, tile_topic(), self.tiles.append, MAP_QOS)
        self.probe.create_subscription(FieldTile, tile_topic("EV1"), self.crew_tiles.append, MAP_QOS)
        self.state = self.probe.create_publisher(CrewState, "/crew/EV1/state", STATE_QOS)
        self.delta = self.probe.create_publisher(CellDelta, DELTA_TOPIC, EVENT_QOS)
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)

    def wait(self, predicate, timeout_s=10.0):
        assert spin_until(self.executor, predicate, timeout_s)

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def crew_state(model, remaining: Resources, xy, frame="map") -> CrewState:
    rates = model.nominal_rates("EV1")
    message = CrewState()
    message.header.frame_id = frame
    message.crew_id = "EV1"
    message.pose.pose.position.x, message.pose.pose.position.y = xy
    c = message.consumables
    c.crew_id = "EV1"
    c.o2_kg, c.co2_capacity_kg = remaining.o2_kg, remaining.co2_capacity_kg
    c.water_kg, c.battery_wh = remaining.water_kg, remaining.battery_wh
    c.o2_rate_kg_h, c.water_rate_kg_h = rates.o2_kg_s * 3600.0, rates.water_kg_s * 3600.0
    c.battery_rate_w = rates.battery_w
    # metabolic power that reproduces the nominal CO2 rate
    speed = model.walk.speed_factor_unobserved * walking_speed(0.0, model.walk)
    c.metabolic_w = metabolic_power(speed, 0.0, model.walk.eta_default, model.crew["EV1"], model.suit, model.walk)
    return message


def low(model, fraction=0.05) -> Resources:
    """Remaining = reserve + fraction of the start amount above reserve (0.05 → 3 of 60 min)."""
    start, reserve = model.start_resources("EV1"), model.eva.reserve
    return Resources(*(r + (s - r) * fraction for s, r in zip(
        (start.o2_kg, start.co2_capacity_kg, start.water_kg, start.battery_wh),
        (reserve.o2_kg, reserve.co2_capacity_kg, reserve.water_kg, reserve.battery_wh))))


def test_start_state_is_published_with_layout_tile_and_no_position(ros, tmp_path):
    paths = write_inputs(tmp_path)
    rig = Rig(paths)
    try:
        rig.wait(lambda: rig.redlines and rig.margins and rig.tiles and rig.crew_tiles)
        redline, margin, tile = rig.redlines[-1], rig.margins[-1], rig.tiles[-1]
        assert redline.header.frame_id == margin.header.frame_id == tile.header.frame_id == "map"
        assert math.isnan(redline.margin_now_min) and redline.limiting_crew_id == ""
        assert redline.limiting_consumable == LIM_NONE and len(redline.abort_regions) == 1
        assert (margin.width, margin.height, margin.resolution_m) == (SHAPE[1], SHAPE[0], 4.0)
        assert (margin.origin.x, margin.origin.y) == ORIGIN and margin.crew_id == "EV1"
        values = np.asarray(margin.margin_min, dtype=float)
        assert values[flat_index(*HABITAT_XY)] == pytest.approx(60.0, rel=1e-6)
        reference = reference_model(paths)
        expected = reference.snapshot({"EV1": CrewInput(reference.start_resources("EV1"),
                                                         reference.nominal_rates("EV1"), None)})
        np.testing.assert_allclose(values.reshape(SHAPE), expected.crews["EV1"].margin.margin_min, rtol=1e-6)
        assert margin.terminate_threshold_min == 10.0
        decoded = decode_tile(bytes(tile.png), tile.scale, tile.offset, tile.nodata_byte)
        assert decoded.shape == SHAPE and tile.name == "margin_min" and tile.unit == "min"
        assert np.max(np.abs(decoded - np.clip(values.reshape(SHAPE), -60, 60))) <= tile.scale / 2 + 1e-4
        assert rig.crew_tiles[-1].name == "margin_min_EV1" and bytes(rig.crew_tiles[-1].png) == bytes(tile.png)
        for ring in redline.abort_regions:
            assert (ring.points[0].x, ring.points[0].y) == (ring.points[-1].x, ring.points[-1].y)
    finally:
        rig.close()


def test_crew_state_sets_margin_now_and_shrinks_the_line(ros, tmp_path):
    paths = write_inputs(tmp_path)
    rig = Rig(paths)
    reference = reference_model(paths)
    try:
        rig.wait(lambda: rig.redlines)
        rig.state.publish(crew_state(reference, low(reference), (42.0, 2.0)))
        rig.wait(lambda: rig.redlines and rig.redlines[-1].limiting_crew_id == "EV1")
        redline = rig.redlines[-1]
        # Topics are not ordered against each other: wait for the margin of the same tick.
        rig.wait(lambda: any(m.header.stamp == redline.header.stamp for m in rig.margins))
        rig.margins[:] = [m for m in rig.margins if m.header.stamp == redline.header.stamp]
        expected = reference.snapshot({"EV1": CrewInput(low(reference), reference.nominal_rates("EV1"),
                                                         (42.0, 2.0))})
        assert redline.margin_now_min == pytest.approx(expected.margin_now_min, rel=1e-5)
        assert 0 < redline.margin_now_min < 3.0 and redline.limiting_consumable == LIM_O2
        safe = np.count_nonzero(np.asarray(rig.margins[-1].margin_min) >= 0)
        assert abs(safe - np.count_nonzero(expected.combined.field.margin_s >= 0)) <= 2  # float32 transport
        assert 0 < safe < SHAPE[0] * SHAPE[1]  # 3 min no longer covers the whole grid
    finally:
        rig.close()


def test_cell_delta_recomputes_and_bad_inputs_are_rejected(ros, tmp_path):
    paths = write_inputs(tmp_path)
    rig = Rig(paths)
    try:
        rig.wait(lambda: rig.margins)
        far, mirror = flat_index(82.0, 2.0), flat_index(-78.0, 2.0)  # same distance east and west of the habitat
        before = np.asarray(rig.margins[-1].margin_min)
        assert before[far] == pytest.approx(before[mirror], abs=1e-4)

        def delta(origin=ORIGIN, frame="map", site="TST", resolution=4.0):
            message = CellDelta()
            message.header.frame_id, message.site_id, message.resolution_m = frame, site, resolution
            message.origin.x, message.origin.y = origin
            message.cells = [CellState(iy=iy, ix=ix, state=DETECTED) for iy in range(25, 36) for ix in range(40, 60)]
            return message

        rig.delta.publish(delta(origin=(-120.0, -116.0)))
        rig.delta.publish(delta(frame="odom"))
        rig.delta.publish(delta(site="BXW"))
        rig.delta.publish(delta(resolution=2.0))
        rig.wait(lambda: rig.node.counts["rejected_deltas"] == 4)
        assert rig.node.model.version == 1

        rig.delta.publish(delta())
        rig.wait(lambda: rig.node.model.version == 2)
        count = len(rig.margins)
        rig.wait(lambda: len(rig.margins) > count)
        after = np.asarray(rig.margins[-1].margin_min)
        assert after[far] > after[mirror] + 0.05  # observed ground on the east side is faster and surer

        bad = crew_state(rig.node.model, rig.node.model.start_resources("EV1"), (10.0, 2.0), frame="odom")
        rig.state.publish(bad)
        rig.wait(lambda: rig.node.counts["rejected_states"] > 0)
        assert rig.redlines[-1].limiting_crew_id == ""  # fell back to the start state without a position
    finally:
        rig.close()


def write_sun(directory, paths):
    """Synthetic SIMULATED sun table: elevation 30° at 00:00Z falling 0.25°/min, so sunset is exactly
    02:00Z; the scenario starts at 01:00Z, so at PET 0 the FR-12 budget is 60 − 30 (dusk) = 30 min."""
    start = datetime(2024, 5, 20, 0, 0, tzinfo=timezone.utc)
    rows = ["utc,sun_az_deg,sun_el_deg,earth_light_time_s"]
    rows += [f"{start + timedelta(minutes=k):%Y-%m-%dT%H:%M:%SZ},270.0000,{30.0 - 0.25 * k:.4f},950.000"
             for k in range(181)]
    table = directory / "sun.csv"
    table.write_text("\n".join(rows) + "\n", encoding="utf-8")
    (directory / "sun.json").write_text(json.dumps({"site": {"lon_east_deg": 137.37},
                                                    "csv_sha256": hashlib.sha256(table.read_bytes()).hexdigest()}))
    scenario = directory / "s.yaml"
    scenario.write_text("id: T\nsite: TST\nseed: 1\ntime_scale: 1\n"
                        "start: {historical_utc: '2024-05-20T01:00:00Z', pet_min: 0}\ncrew: [EV1]\n")
    return {**paths, "sun_table": str(table), "scenario_file": str(scenario)}


def test_sun_table_daylight_term_limits_the_margin_until_and_after_dusk(ros, tmp_path):
    paths = write_sun(tmp_path, write_inputs(tmp_path))
    rig = Rig(paths)
    reference = reference_model(paths)
    clock_pub = rig.probe.create_publisher(Clock, "/redline/mission/clock", STATE_QOS)

    def at_pet(seconds):
        message = Clock()
        message.clock.sec = seconds
        rig.wait(lambda: (clock_pub.publish(message), rig.node.pet_s == seconds)[1])

    try:
        rig.wait(lambda: rig.redlines)
        assert math.isnan(rig.node.daylight_budget_s)  # no mission clock yet: term not applied
        at_pet(0)
        start = reference.start_resources("EV1")
        rig.state.publish(crew_state(reference, start, (42.0, 2.0)))
        rig.wait(lambda: rig.redlines[-1].limiting_consumable == LIM_DAYLIGHT)
        assert rig.node.daylight_budget_s == pytest.approx(1800.0, abs=1e-6)
        expected = reference.snapshot({"EV1": CrewInput(start, reference.nominal_rates("EV1"), (42.0, 2.0))},
                                      daylight_budget_s=1800.0)
        assert rig.redlines[-1].margin_now_min == pytest.approx(expected.margin_now_min, rel=1e-5)
        assert 25.0 < rig.redlines[-1].margin_now_min < 30.0  # 30 min budget less the ~1 min walk home
        at_pet(3700)  # 02:01:40Z, Sun below the horizon: nowhere is within the dusk limit
        rig.state.publish(crew_state(reference, start, (42.0, 2.0)))
        rig.wait(lambda: rig.redlines[-1].margin_now_min == -math.inf)
        assert rig.node.daylight_budget_s == -math.inf and rig.redlines[-1].limiting_consumable == LIM_DAYLIGHT
        assert len(rig.redlines[-1].abort_regions) == 0
    finally:
        rig.close()


def test_rejects_a_grid_for_another_site(ros, tmp_path):
    paths = write_inputs(tmp_path)
    (tmp_path / "eva.yaml").write_text((tmp_path / "eva.yaml").read_text().replace("site_id: TST", "site_id: BXW"))
    with pytest.raises(ValueError, match="site"):
        WalkbackFieldNode(parameter_overrides=[Parameter(k, value=v) for k, v in paths.items()])


# --- D015: blocked deltas, scenario crew list, leak factor -----------------------------------
def test_a_blocked_delta_cuts_the_field_behind_a_wall(ros, tmp_path):
    paths = write_inputs(tmp_path)
    rig = Rig(paths)
    try:
        rig.wait(lambda: rig.margins)
        east = flat_index(82.0, 2.0)
        assert math.isfinite(np.asarray(rig.margins[-1].margin_min)[east])
        message = CellDelta()
        message.header.frame_id, message.site_id, message.resolution_m = "map", "TST", 4.0
        message.origin.x, message.origin.y = ORIGIN
        message.cells = [CellState(iy=iy, ix=45, state=DETECTED, speed_factor=0.0, evidence_id="ev-wall")
                         for iy in range(SHAPE[0])]
        rig.delta.publish(message)
        rig.wait(lambda: rig.node.model.version == 2)
        count = len(rig.margins)
        rig.wait(lambda: len(rig.margins) > count)
        assert math.isnan(np.asarray(rig.margins[-1].margin_min)[east])  # unreachable behind the wall
    finally:
        rig.close()


def test_crew_ids_parameter_adds_the_scenario_crew(ros, tmp_path):
    paths = write_inputs(tmp_path)
    (tmp_path / "crew.yaml").write_text("provenance_status: SCENARIO\ncrew:\n"
                                        "  EV1: {body_mass_kg: 75.0, load_mass_kg: 80.0, theta: 1.0}\n"
                                        "  EV2: {body_mass_kg: 68.0, load_mass_kg: 80.0, theta: 1.0}\n")
    node = WalkbackFieldNode(parameter_overrides=[Parameter(k, value=v) for k, v in paths.items()] +
                             [Parameter("crew_ids", value=["EV1", "EV2"])])
    try:
        assert node.eva.crew_ids == ("EV1", "EV2") and set(node.model.crew) == {"EV1", "EV2"}
    finally:
        node.destroy_node()


def test_a_suit_leak_in_the_consumables_scales_the_o2_needed_to_walk_back(ros, tmp_path):
    paths = write_inputs(tmp_path)
    rig = Rig(paths)
    reference = reference_model(paths)
    try:
        rig.wait(lambda: rig.redlines)
        message = crew_state(reference, low(reference, 0.5), (42.0, 2.0))
        message.consumables.o2_rate_kg_h *= 3.0  # SUIT_LEAK ×3; metabolic power unchanged
        rig.state.publish(message)
        rig.wait(lambda: rig.redlines[-1].limiting_crew_id == "EV1")
        rates = reference.nominal_rates("EV1")
        leak = type(rates)(3.0 * rates.o2_kg_s, rates.co2_kg_s, rates.water_kg_s, rates.battery_w)
        expected = reference.snapshot({"EV1": CrewInput(low(reference, 0.5), leak, (42.0, 2.0), o2_need_factor=3.0)})
        assert rig.redlines[-1].margin_now_min == pytest.approx(expected.margin_now_min, rel=1e-4)
        assert rig.redlines[-1].limiting_consumable == LIM_O2
    finally:
        rig.close()
