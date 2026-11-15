"""mission_manager nominal flow over real DDS (proje.md §8.7; D015)."""
import json
import time

import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock

from redline_mission.mission_manager import DECISION_TOPIC, EVENT_QOS, MAP_QOS, STATE_QOS, STATE_TOPIC, \
    MissionManagerNode
from redline_msgs.msg import CrewState, DecisionRecord, EVAPlan, MissionState, PlanLeg, Station
from redline_msgs.srv import PlanEva, ScenarioControl


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def plan() -> EVAPlan:
    """HAB (2, 2) -> S1 (42, 2) -> HAB; 60 s legs, 30 s service; egress at PET 0."""
    message = EVAPlan()
    message.header.frame_id, message.plan_id, message.version, message.site_id = "map", "plan-TST-0001", 1, "TST"
    station = Station()
    station.station_id, station.target_id, station.service_min = "S1", "TST-T01", 0.5
    station.position.x, station.position.y = 42.0, 2.0
    message.stations = [station]
    for a, b in (("HAB", "S1"), ("S1", "HAB")):
        leg = PlanLeg()
        leg.from_id, leg.to_id, leg.duration_min = a, b, 1.0
        message.legs.append(leg)
    for x in list(range(2, 43, 4)) + list(range(38, 1, -4)):
        pose = PoseStamped()
        pose.pose.position.x, pose.pose.position.y = float(x), 2.0
        message.route.poses.append(pose)
    return message


class Rig:
    def __init__(self):
        self.node = MissionManagerNode(parameter_overrides=[
            Parameter("nominal_flow", value=True), Parameter("initial_phase", value="BRIEFING"),
            Parameter("crew_ids", value=["EV1", "EV2"]), Parameter("site_id", value="TST"),
            Parameter("egress_pet_s", value=0.0), Parameter("run_id", value="run-T")])
        self.probe = rclpy.create_node("probe")
        self.states, self.decisions, self.requests, self.controls = [], [], [], []
        self.probe.create_subscription(MissionState, STATE_TOPIC, self.states.append, MAP_QOS)
        self.probe.create_subscription(DecisionRecord, DECISION_TOPIC, self.decisions.append, EVENT_QOS)
        self.probe.create_service(PlanEva, "/redline/plan_eva", self._plan)
        self.probe.create_service(ScenarioControl, "/redline/scenario/control", self._control)
        self.clock = self.probe.create_publisher(Clock, "/redline/mission/clock", STATE_QOS)
        self.crew = {c: self.probe.create_publisher(CrewState, f"/crew/{c}/state", STATE_QOS) for c in ("EV1", "EV2")}
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)

    def _plan(self, request, response):
        self.requests.append(request)
        response.success, response.plan = True, plan()
        return response

    def _control(self, request, response):
        self.controls.append(request.command)
        response.success = True
        return response

    def spin(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.01)

    def until(self, predicate, timeout=8.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.01)
            if predicate():
                return
        raise AssertionError("condition not reached")

    def at(self, pet, xy):
        for c, pub in self.crew.items():
            message = CrewState()
            message.header.frame_id, message.crew_id = "map", c
            message.pose.pose.position.x, message.pose.pose.position.y = xy
            pub.publish(message)
        clock = Clock()
        clock.clock.sec = int(pet)
        self.clock.publish(clock)
        self.spin(0.8)

    def phase(self):
        return self.states[-1].phase

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def test_nominal_flow_plans_starts_the_clock_and_walks_through_the_phases(ros):
    rig = Rig()
    try:
        rig.until(lambda: rig.states and rig.phase() == MissionState.TRAVERSE)
        assert rig.requests and rig.requests[0].site_id == "TST" and list(rig.requests[0].crew_ids) == ["EV1", "EV2"]
        rig.until(lambda: ScenarioControl.Request.START in rig.controls)
        assert rig.states[-1].active_plan_id == "plan-TST-0001"
        rig.at(70.0, (42.0, 2.0))  # schedule: S1 service 60-90 s
        assert rig.phase() == MissionState.STATION_SCIENCE
        rig.at(95.0, (30.0, 2.0))
        assert rig.phase() == MissionState.RETURN  # S1 was the last station
        rig.at(160.0, (2.0, 2.0))
        assert rig.phase() == MissionState.DEBRIEF
        contexts = [d.context for d in rig.decisions]
        assert contexts == ["plan accepted; egress", "arrived at S1", "S1 done; last station, walking home",
                            "crew in shelter"]
        assert json.loads(rig.decisions[0].assumptions_json)["plan_id"] == "plan-TST-0001"
    finally:
        rig.close()


def test_nominal_flow_and_the_orientation_walkthrough_are_exclusive(ros):
    with pytest.raises(ValueError, match="orientation"):
        MissionManagerNode(parameter_overrides=[Parameter("nominal_flow", value=True),
                                                Parameter("intro_enabled", value=True),
                                                Parameter("initial_phase", value="BRIEFING")])
