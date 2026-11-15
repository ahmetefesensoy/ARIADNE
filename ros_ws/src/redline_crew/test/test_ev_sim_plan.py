"""ev_sim plan mode over real DDS (D015): SIMULATED walk on PET, trail, leak, contingency return, ingress."""
import math
import time

import numpy as np
import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

from redline_core.grid import Grid
from redline_core.planning import save_planning_grid
from redline_core.redline import Rates
from redline_core.scenario import ScenarioEvent, encode_event
from redline_crew.ev_sim import MISSION_CLOCK_TOPIC, POSE_QOS, STATE_QOS, EvSimNode
from redline_msgs.msg import Alert, CrewState, EVAPlan, MissionState, PlanLeg, Station

MAP_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
EVENT_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
EVA = """provenance_status: SCENARIO
site_id: TST
crew_ids: [EV1]
habitat: {requested_xy_m: [0.0, 0.0], placement: nearest_in_largest_component}
reserve: {o2_kg: 0.1, co2_capacity_kg: 0.0, water_kg: 0.0, battery_wh: 0.0}
start: {minutes_above_reserve: 60.0}
lines: {terminate_threshold_min: 10.0, simplify_tolerance_m: 0.0}
tile: {lo_min: -60.0, hi_min: 60.0, bit_depth: 8}
sigma_fallback_percentile: 95.0
"""
HOME = (2.0, 2.0)  # habitat cell (30, 30) centre on the 60x60, 4 m grid at origin (-120, -120)


@pytest.fixture
def files(tmp_path):
    (tmp_path / "crew.yaml").write_text("provenance_status: SCENARIO\ncrew:\n"
                                        "  EV1: {body_mass_kg: 75.0, load_mass_kg: 80.0, theta: 1.0}\n"
                                        "  EV2: {body_mass_kg: 68.0, load_mass_kg: 80.0, theta: 1.0}\n")
    (tmp_path / "suit.yaml").write_text("provenance_status: SCENARIO\nwalk: {}\nsuit: {}\n")
    (tmp_path / "eva.yaml").write_text(EVA)
    shape = (60, 60)
    layers = {"z_m": np.zeros(shape), "slope_deg": np.zeros(shape), "slope_sigma_deg": np.full(shape, 0.5),
              "relief_m": np.zeros(shape), "wall_slope_deg": np.zeros(shape)}
    save_planning_grid(tmp_path / "grid", Grid((-120.0, -120.0), 4.0, 60, 60, layers),
                       {"status": "SIMULATED", "site_id": "TST", "note": "synthetic flat test grid"})
    return tmp_path


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def plan_message() -> EVAPlan:
    """HAB (2, 2) -> S1 (42, 2) -> HAB; 60 s per leg, 30 s service."""
    plan = EVAPlan()
    plan.header.frame_id, plan.plan_id, plan.version, plan.site_id = "map", "plan-TST-0001", 1, "TST"
    station = Station()
    station.station_id, station.target_id = "S1", "TST-T01"
    station.position.x, station.position.y = 42.0, 2.0
    station.service_min = 0.5
    plan.stations = [station]
    for a, b in (("HAB", "S1"), ("S1", "HAB")):
        leg = PlanLeg()
        leg.from_id, leg.to_id, leg.duration_min = a, b, 1.0
        plan.legs.append(leg)
    for x in list(range(2, 43, 4)) + list(range(38, 1, -4)):
        pose = PoseStamped()
        pose.pose.position.x, pose.pose.position.y = float(x), 2.0
        plan.route.poses.append(pose)
    return plan


class Rig:
    def __init__(self, files, crew_id="EV1", trail_s=0.0, extra_pose_publisher=False):
        self.node = EvSimNode(parameter_overrides=[
            Parameter("crew_id", value=crew_id), Parameter("motion", value="plan"),
            Parameter("trail_s", value=trail_s), Parameter("rate_hz", value=20.0),
            Parameter("crew_file", value=str(files / "crew.yaml")),
            Parameter("suit_file", value=str(files / "suit.yaml")),
            Parameter("eva_file", value=str(files / "eva.yaml")),
            Parameter("planning_grid", value=str(files / "grid.npz"))])
        self.probe = rclpy.create_node("probe")
        self.poses, self.states = [], []
        self.probe.create_subscription(PoseStamped, f"/crew/{crew_id}/pose", self.poses.append, POSE_QOS)
        self.probe.create_subscription(CrewState, f"/crew/{crew_id}/state", self.states.append, STATE_QOS)
        if extra_pose_publisher:
            self.other = self.probe.create_publisher(PoseStamped, f"/crew/{crew_id}/pose", POSE_QOS)
        self.clock = self.probe.create_publisher(Clock, MISSION_CLOCK_TOPIC, STATE_QOS)
        self.phase = self.probe.create_publisher(MissionState, "/redline/mission/state", MAP_QOS)
        self.plan = self.probe.create_publisher(EVAPlan, "/redline/plan", MAP_QOS)
        self.events = self.probe.create_publisher(Alert, "/redline/scenario/event", EVENT_QOS)
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)
        self.plan.publish(plan_message())
        self.spin(0.5)

    def spin(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.01)

    def at(self, pet, phase=None, tasks=()):
        if phase is not None:
            message = MissionState()
            message.phase = phase
            message.active_task_ids = list(tasks)
            self.phase.publish(message)
        clock = Clock()
        clock.clock.sec, clock.clock.nanosec = int(pet), int(round((pet - int(pet)) * 1e9))
        self.clock.publish(clock)
        self.spin(0.3)

    def last_xy(self):
        p = self.poses[-1].pose.position
        return p.x, p.y

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def o2_rate_from_metabolic(c, suit):
    return Rates.from_metabolic_power(c.metabolic_w, suit).o2_kg_s * 3600.0


def test_plan_mode_walks_the_schedule_from_traverse_and_publishes_its_pose(ros, files):
    rig = Rig(files)
    try:
        rig.at(100.0, MissionState.BRIEFING)
        assert not rig.states  # before egress: no consumption, no state
        rig.at(100.0, MissionState.TRAVERSE)  # the schedule starts at PET 100
        rig.at(130.0)
        assert rig.last_xy() == pytest.approx((22.0, 2.0), abs=0.3)  # half of the 40 m leg
        first = rig.states[0].consumables.o2_kg
        rig.at(170.0)
        assert rig.last_xy() == pytest.approx((42.0, 2.0), abs=0.3)  # serving at S1 (160-190 s)
        assert rig.states[-1].consumables.o2_kg < first
        assert rig.poses[-1].header.frame_id == "map"
    finally:
        rig.close()


def test_a_trailing_crew_member_walks_the_same_schedule_later(ros, files):
    rig = Rig(files, crew_id="EV2", trail_s=20.0)
    try:
        rig.at(100.0, MissionState.TRAVERSE)
        rig.at(130.0)
        assert rig.last_xy() == pytest.approx((2.0 + 40.0 * 10.0 / 60.0, 2.0), abs=0.3)
    finally:
        rig.close()


def test_a_suit_leak_event_multiplies_only_this_crew_members_o2_rate(ros, files):
    rig = Rig(files)
    try:
        rig.at(100.0, MissionState.TRAVERSE)
        rig.at(110.0)
        c = rig.states[-1].consumables
        assert c.o2_rate_kg_h == pytest.approx(o2_rate_from_metabolic(c, rig.node.suit), rel=1e-6)
        for crew_id in ("EV2", "EV1"):
            alert = Alert()
            alert.code = "SUIT_LEAK"
            alert.text = encode_event(ScenarioEvent(1.0, "SUIT_LEAK", {"crew_id": crew_id, "k_leak": 3.0}), "leak")
            rig.events.publish(alert)
            rig.at(115.0)
            if crew_id == "EV2":  # another crew member's leak leaves this suit unchanged
                c = rig.states[-1].consumables
                assert c.o2_rate_kg_h == pytest.approx(o2_rate_from_metabolic(c, rig.node.suit), rel=1e-6)
        c = rig.states[-1].consumables
        assert c.o2_rate_kg_h == pytest.approx(3.0 * o2_rate_from_metabolic(c, rig.node.suit), rel=1e-6)
    finally:
        rig.close()


def test_contingency_walks_home_and_debrief_at_home_stops_consumption(ros, files):
    rig = Rig(files)
    try:
        rig.at(100.0, MissionState.TRAVERSE)
        rig.at(130.0)
        out = rig.last_xy()
        rig.at(130.0, MissionState.CONTINGENCY)
        rig.at(140.0, MissionState.RETURN)
        now = rig.last_xy()
        assert math.hypot(now[0] - HOME[0], now[1] - HOME[1]) < math.hypot(out[0] - HOME[0], out[1] - HOME[1])
        rig.at(400.0)
        assert rig.last_xy() == pytest.approx(HOME, abs=0.5)
        rig.at(400.0, MissionState.DEBRIEF)
        rig.at(410.0)
        kept = rig.states[-1].consumables.o2_kg
        rig.at(900.0)
        assert rig.states[-1].consumables.o2_kg == pytest.approx(kept)  # ingress: the suit is off
    finally:
        rig.close()


def test_refuses_to_publish_poses_when_another_publisher_owns_the_topic(ros, files):
    rig = Rig(files, extra_pose_publisher=True)
    try:
        rig.at(100.0, MissionState.TRAVERSE)
        rig.at(130.0)
        assert not rig.poses and rig.node.counts["pose_conflicts"] > 0
    finally:
        rig.close()


def test_egress_pet_parameter_fixes_the_schedule_start_against_clock_races(ros, files):
    rig = Rig(files)
    rig.node.egress_pet_s = 100.0  # what the launch passes: the scenario start PET
    try:
        rig.at(130.0, MissionState.TRAVERSE)  # TRAVERSE seen only after the clock moved on
        rig.at(130.0)
        assert rig.last_xy() == pytest.approx((22.0, 2.0), abs=0.3)  # still the schedule from PET 100
    finally:
        rig.close()


def test_a_shelter_return_task_sends_the_crew_home_even_if_contingency_was_too_brief_to_see(ros, files):
    """S2 on BXW (2026-11-15): mission_manager left CONTINGENCY for RETURN within milliseconds of the
    ReturnToShelter goal being accepted; ev_sim saw only RETURN, took it for the plan's last leg and
    kept walking the stations, so EV2's leak margin went to -94 min. A RETURN with an active
    shelter task is a contingency return."""
    rig = Rig(files)
    try:
        rig.at(100.0, MissionState.TRAVERSE)
        rig.at(130.0)
        out = rig.last_xy()
        rig.at(130.0, MissionState.RETURN, tasks=["rts-run-0002"])
        rig.at(140.0)
        now = rig.last_xy()
        assert math.hypot(now[0] - HOME[0], now[1] - HOME[1]) < math.hypot(out[0] - HOME[0], out[1] - HOME[1])
        rig.at(400.0)
        assert rig.last_xy() == pytest.approx(HOME, abs=0.5)
    finally:
        rig.close()
