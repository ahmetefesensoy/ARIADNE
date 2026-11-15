"""ev_sim over real DDS: egress on first pose, consumption only over mission/PET time."""
import math
import time

import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock

from redline_core.cost_human import CrewMember, SuitModel, WalkModel
from redline_core.suit_state import Motion, consumption
from redline_crew.ev_sim import MISSION_CLOCK_TOPIC, POSE_QOS, STATE_QOS, EvSimNode
from redline_msgs.msg import CrewState

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


@pytest.fixture
def configs(tmp_path):
    (tmp_path / "crew.yaml").write_text(
        "provenance_status: SCENARIO\ncrew:\n  EV1: {body_mass_kg: 75.0, load_mass_kg: 80.0, theta: 1.0}\n")
    (tmp_path / "suit.yaml").write_text("provenance_status: SCENARIO\nwalk: {}\nsuit: {}\n")
    (tmp_path / "eva.yaml").write_text(EVA)
    return tmp_path


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


class Rig:
    def __init__(self, configs, *, scenario_cap=0.0):
        self.node = EvSimNode(parameter_overrides=[
            Parameter("crew_file", value=str(configs / "crew.yaml")),
            Parameter("suit_file", value=str(configs / "suit.yaml")),
            Parameter("eva_file", value=str(configs / "eva.yaml")),
            Parameter("rate_hz", value=20.0),
            Parameter("scenario_pose_speed_cap_m_s", value=scenario_cap),
        ])
        self.probe = rclpy.create_node("probe")
        self.clock = self.probe.create_publisher(Clock, MISSION_CLOCK_TOPIC, STATE_QOS)
        self.pose = self.probe.create_publisher(PoseStamped, "/crew/EV1/pose", POSE_QOS)
        self.states = []
        self.probe.create_subscription(CrewState, "/crew/EV1/state", self.states.append, STATE_QOS)
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)

    def spin(self, seconds, until=None):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.01)
            if until is not None and until():
                return True
        return until is None

    def send_clock(self, pet):
        message = Clock()
        message.clock.sec = int(pet)
        message.clock.nanosec = int(round((pet - int(pet)) * 1e9))
        self.clock.publish(message)

    def send_pose(self, x, y, z=0.0, frame="map"):
        message = PoseStamped()
        message.header.frame_id = frame
        message.pose.position.x, message.pose.position.y, message.pose.position.z = x, y, z
        message.pose.orientation.w = 1.0
        self.pose.publish(message)

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def test_consumption_starts_at_egress_and_follows_pet_only(ros, configs):
    rig = Rig(configs)
    try:
        assert rig.spin(1.0, lambda: rig.probe.count_publishers(MISSION_CLOCK_TOPIC) > 0 and
                        rig.node.count_publishers("/crew/EV1/pose") > 0)
        rig.send_clock(0.0)
        rig.spin(0.5)
        assert rig.states == []  # no pose yet: no state, nothing consumed

        rig.send_pose(10.0, 20.0)
        assert rig.spin(5.0, lambda: len(rig.states) >= 3)
        first = rig.states[-1]
        start = rig.node.start
        assert first.consumables.o2_kg == pytest.approx(start.o2_kg, rel=1e-6)
        assert (first.pose.pose.position.x, first.pose.pose.position.y) == (10.0, 20.0)
        assert first.header.frame_id == "map" and first.crew_id == "EV1"
        assert math.isnan(first.heart_rate_bpm)

        # Wall time passes but PET does not: nothing is consumed.
        rig.spin(0.5)
        assert rig.states[-1].consumables.o2_kg == pytest.approx(first.consumables.o2_kg, rel=1e-7)

        # PET jumps 600 s while standing: the standing rates apply to the whole interval.
        member, walk, suit = CrewMember("EV1", 75.0, 80.0), WalkModel(), SuitModel()
        power, rates = consumption(Motion(0.0, 0.0, False), walk.eta_default, member, suit, walk)
        assert first.consumables.metabolic_w == pytest.approx(power, rel=1e-5)
        rig.send_clock(600.0)
        assert rig.spin(5.0, lambda: rig.states[-1].consumables.o2_kg < first.consumables.o2_kg)
        after = rig.states[-1].consumables
        assert first.consumables.o2_kg - after.o2_kg == pytest.approx(rates.o2_kg_s * 600.0, rel=1e-4)
        assert first.consumables.battery_wh - after.battery_wh == pytest.approx(rates.battery_w / 6.0, rel=1e-4)

        # PET moving back consumes nothing and is counted.
        rig.send_clock(300.0)
        rig.spin(0.5)
        assert rig.node.counts["pet_backwards"] == 1
        assert rig.states[-1].consumables.o2_kg == pytest.approx(after.o2_kg, rel=1e-7)
    finally:
        rig.close()


def test_walking_raises_metabolic_power_and_bad_poses_are_rejected(ros, configs):
    rig = Rig(configs)
    try:
        rig.spin(1.0, lambda: rig.node.count_publishers("/crew/EV1/pose") > 0)
        rig.send_clock(0.0)
        rig.send_pose(0.0, 0.0)
        assert rig.spin(5.0, lambda: len(rig.states) >= 2)
        standing = rig.states[-1].consumables.metabolic_w
        start = time.monotonic()
        while time.monotonic() - start < 1.5:  # 0.8 m/s east at ~20 Hz
            rig.send_pose(0.8 * (time.monotonic() - start), 0.0)
            rig.spin(0.05)
        rig.spin(0.2)
        walking = rig.states[-1].consumables
        # D010: standing ≈ 236 W; walking adds the Pandolf term and the speed-proportional suit cost.
        member, walk, suit = CrewMember("EV1", 75.0, 80.0), WalkModel(), SuitModel()
        measured = rig.node.window.motion(walk)  # receipt timing makes this close to, not exactly, 0.8
        assert measured.speed_m_s == pytest.approx(0.8, rel=0.1)
        expected, _ = consumption(measured, walk.eta_default, member, suit, walk)
        assert walking.metabolic_w > standing + 150.0
        assert walking.metabolic_w == pytest.approx(expected, rel=1e-4)
        assert walking.o2_rate_kg_h > rig.states[1].consumables.o2_rate_kg_h

        poses_before = rig.node.counts["poses"]
        rig.send_pose(500.0, 0.0, frame="odom")
        rig.send_pose(math.nan, 0.0)
        rig.spin(0.5)
        assert rig.node.counts["rejected_poses"] == 2 and rig.node.counts["poses"] == poses_before
        assert rig.states[-1].pose.pose.position.x < 5.0
    finally:
        rig.close()


def test_requires_configs_and_a_known_crew_id(ros, configs):
    with pytest.raises(ValueError):
        EvSimNode()
    with pytest.raises(ValueError):
        EvSimNode(parameter_overrides=[
            Parameter("crew_id", value="EV9"),
            Parameter("crew_file", value=str(configs / "crew.yaml")),
            Parameter("suit_file", value=str(configs / "suit.yaml")),
            Parameter("eva_file", value=str(configs / "eva.yaml")),
        ])


def test_scenario_sprint_metering_increases_reported_consumption(ros, configs):
    rig = Rig(configs, scenario_cap=3.0)
    try:
        rig.spin(1.0, lambda: rig.node.count_publishers("/crew/EV1/pose") > 0)
        rig.send_clock(0.0)
        rig.send_pose(0.0, 0.0)
        assert rig.spin(5.0, lambda: len(rig.states) >= 2)
        start = time.monotonic()
        while time.monotonic() - start < 1.5:
            rig.send_pose(3.0 * (time.monotonic() - start), 0.0)
            rig.spin(0.05)
        rig.spin(0.2)
        measured = rig.node.window.motion(rig.node.walk)
        assert measured.speed_m_s == pytest.approx(3.0, rel=0.1)
        # At 20 Hz the DDS receipt timestamps jitter slightly around the cap.
        assert measured.speed_m_s > 2 * rig.node.walk.walk_run_speed_m_s
        expected, _ = consumption(measured, rig.node.walk.eta_default,
                                  rig.node.member, rig.node.suit, rig.node.walk)
        assert rig.states[-1].consumables.metabolic_w == pytest.approx(expected, rel=1e-4)
        assert rig.node.counts["scenario_extrapolated_ticks"] > 0
        before = rig.states[-1].consumables.o2_kg
        rig.send_clock(10.0)
        assert rig.spin(5.0, lambda: rig.states[-1].consumables.o2_kg < before)
    finally:
        rig.close()


@pytest.mark.parametrize("cap", [-1.0, math.nan, math.inf, 5.01])
def test_scenario_sprint_cap_is_bounded_at_the_ros_boundary(ros, configs, cap):
    with pytest.raises(ValueError, match="scenario_pose_speed_cap_m_s"):
        EvSimNode(parameter_overrides=[
            Parameter("crew_file", value=str(configs / "crew.yaml")),
            Parameter("suit_file", value=str(configs / "suit.yaml")),
            Parameter("eva_file", value=str(configs / "eva.yaml")),
            Parameter("scenario_pose_speed_cap_m_s", value=cap),
        ])


def test_scenario_sprint_cap_cannot_change_plan_mode(ros, configs):
    with pytest.raises(ValueError, match="only for motion 'pose'"):
        EvSimNode(parameter_overrides=[
            Parameter("crew_file", value=str(configs / "crew.yaml")),
            Parameter("suit_file", value=str(configs / "suit.yaml")),
            Parameter("eva_file", value=str(configs / "eva.yaml")),
            Parameter("motion", value="plan"),
            Parameter("scenario_pose_speed_cap_m_s", value=3.0),
        ])
