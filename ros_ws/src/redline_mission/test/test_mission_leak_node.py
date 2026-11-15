"""mission_manager answers a telemetry SUIT_LEAK alert (proje.md §8.7, §16 S2) over real DDS:
CONTINGENCY → ReturnToShelter for the whole crew → RETURN → DEBRIEF, each with a DecisionRecord."""
import json
import time

import pytest
import rclpy
from rclpy.action import ActionServer
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter

from redline_mission.mission_manager import ALERT_TOPIC, DECISION_TOPIC, EVENT_QOS, MAP_QOS, STATE_TOPIC, \
    MissionManagerNode
from redline_msgs.action import ReturnToShelter
from redline_msgs.msg import Alert, DecisionRecord, MissionState


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


class Rig:
    def __init__(self, initial_phase="TRAVERSE"):
        self.node = MissionManagerNode(parameter_overrides=[
            Parameter("crew_ids", value=["EV1", "EV2"]), Parameter("run_id", value="run-L"),
            Parameter("initial_phase", value=initial_phase)])
        self.probe = rclpy.create_node("probe")
        self.states, self.decisions, self.goals = [], [], []
        self.probe.create_subscription(MissionState, STATE_TOPIC, self.states.append, MAP_QOS)
        self.probe.create_subscription(DecisionRecord, DECISION_TOPIC, self.decisions.append, EVENT_QOS)
        self.alerts = self.probe.create_publisher(Alert, ALERT_TOPIC, EVENT_QOS)
        ActionServer(self.probe, ReturnToShelter, "/redline/return_to_shelter", self._rts)
        self.executor = MultiThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)
        self.until(lambda: self.states)

    def _rts(self, handle):
        self.goals.append(handle.request)
        handle.succeed()
        result = ReturnToShelter.Result()
        result.outcome, result.actual_time_min = ReturnToShelter.Result.SUCCEEDED, 12.5
        return result

    def alert(self, code="SUIT_LEAK", severity=Alert.WARNING, crew="EV2"):
        message = Alert()
        message.alert_id, message.code, message.severity = f"alert-{code}-{crew}", code, severity
        message.text, message.related_ids = f"{crew} suit leak: O2 rate 3.00x the metabolic model", [crew]
        self.alerts.publish(message)

    def until(self, predicate, timeout=10.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.01)
            if predicate():
                return True
        raise AssertionError("condition not reached")

    def spin(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.01)

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def test_a_suit_leak_alert_sends_the_whole_crew_home_and_records_why(ros):
    rig = Rig()
    try:
        rig.alert()
        rig.until(lambda: rig.states[-1].phase == MissionState.DEBRIEF)
        phases = [s.phase for s in rig.states]
        assert MissionState.CONTINGENCY in phases and MissionState.RETURN in phases
        (goal,) = rig.goals
        assert list(goal.crew_ids) == ["EV1", "EV2"] and goal.shelter_id == "habitat"
        rig.until(lambda: any(d.context == "SUIT_LEAK" for d in rig.decisions))
        leak = next(d for d in rig.decisions if d.context == "SUIT_LEAK")
        assumptions = json.loads(leak.assumptions_json)
        assert assumptions["leak_crew_ids"] == ["EV2"] and assumptions["alert_id"] == "alert-SUIT_LEAK-EV2"
        assert leak.chosen == "ReturnToShelter habitat"
    finally:
        rig.close()


def test_a_caution_a_foreign_code_or_a_leak_before_egress_does_not_end_the_eva(ros):
    rig = Rig()
    try:
        rig.alert(severity=Alert.CAUTION)
        rig.alert(code="SEP_ALERT")  # SEP is answered from /env/dose_rate, not from echoed alerts
        rig.spin(1.0)
        assert rig.states[-1].phase == MissionState.TRAVERSE and not rig.goals
    finally:
        rig.close()
    briefing = Rig(initial_phase="BRIEFING")
    try:
        briefing.alert()
        briefing.spin(1.0)
        assert briefing.states[-1].phase == MissionState.BRIEFING and not briefing.goals
    finally:
        briefing.close()
