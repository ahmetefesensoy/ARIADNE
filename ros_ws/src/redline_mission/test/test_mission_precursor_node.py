"""mission_manager PRECURSOR over real DDS (proje.md §18 T7; D015): proposal → scout → evidence gate → replan."""
import json
import time
from concurrent.futures import Future

import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.action import ActionServer
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from redline_mission.mission_manager import DECISION_TOPIC, EVENT_QOS, MAP_QOS, STATE_TOPIC, MissionManagerNode
from redline_msgs.action import ExecuteScout
from redline_msgs.msg import CellDelta, CellState, DecisionRecord, EVAPlan, MissionState, PlanLeg, Station
from redline_msgs.srv import PlanEva, ScenarioControl

LATCHED = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
ORIGIN, RES = (-120.0, -120.0), 4.0


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def plan(version, ys) -> EVAPlan:
    """HAB (2, 2) -> S1 (42, 2) -> HAB along y values `ys` (v2 detours north)."""
    message = EVAPlan()
    message.header.frame_id, message.plan_id, message.version, message.site_id = "map", f"plan-TST-{version:04d}", \
        version, "TST"
    message.decision_id = f"dec-plan-TST-{version:04d}"
    station = Station()
    station.station_id, station.target_id, station.service_min = "S1", "TST-T01", 0.5
    station.position.x, station.position.y = 42.0, 2.0
    message.stations = [station]
    for a, b, margin in (("HAB", "S1", 50.0 - version), ("S1", "HAB", 48.0 - version)):
        leg = PlanLeg()
        leg.from_id, leg.to_id, leg.duration_min, leg.return_margin_min = a, b, 1.0, margin
        message.legs.append(leg)
    outbound = [(float(x), ys if 2 < x < 42 else 2.0) for x in range(2, 43, 4)]  # detour mid-leg, reach S1
    for x, y in outbound + [(float(x), 2.0) for x in range(38, 1, -4)]:
        pose = PoseStamped()
        pose.pose.position.x, pose.pose.position.y = x, y
        message.route.poses.append(pose)
    return message


class Rig:
    def __init__(self, blocked_on_route: bool, outcome: int = ExecuteScout.Result.SUCCEEDED, abort: bool = False,
                 *, empty=False, publish_known=True):
        self.outcome, self.abort = outcome, abort
        self.empty, self.publish_known = empty, publish_known
        self.node = MissionManagerNode(parameter_overrides=[
            Parameter("nominal_flow", value=True), Parameter("precursor", value=True),
            Parameter("initial_phase", value="BRIEFING"), Parameter("crew_ids", value=["EV1"]),
            Parameter("site_id", value="TST"), Parameter("run_id", value="run-P")])
        self.probe = rclpy.create_node("probe")
        self.blocked_on_route = blocked_on_route
        self.states, self.decisions, self.plan_calls, self.goals = [], [], 0, []
        self.probe.create_subscription(MissionState, STATE_TOPIC, self.states.append, MAP_QOS)
        self.probe.create_subscription(DecisionRecord, DECISION_TOPIC, self.decisions.append, EVENT_QOS)
        self.planner_decisions = self.probe.create_publisher(DecisionRecord, DECISION_TOPIC, EVENT_QOS)
        self.proposals = self.probe.create_publisher(DecisionRecord, "/redline/robot_tasks/proposed", LATCHED)
        self.known = self.probe.create_publisher(CellDelta, "/redline/cells/known", LATCHED)
        self.probe.create_service(PlanEva, "/redline/plan_eva", self._plan)
        self.probe.create_service(ScenarioControl, "/redline/scenario/control", lambda rq, rs: setattr(
            rs, "success", True) or rs)
        ActionServer(self.probe, ExecuteScout, "/scout_1/execute_scout", self._scout)
        self.executor = MultiThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)

    def _plan(self, request, response):
        self.plan_calls += 1
        response.success = True
        response.plan = plan(1, 2.0) if self.plan_calls == 1 else plan(2, 10.0)
        record = DecisionRecord()
        record.decision_id = response.plan.decision_id
        record.context = "PlanEva objective=SCIENCE"
        # The planner names the evidence it applied; the first replan attempt has not seen it yet.
        record.evidence_ids = ["scout-run-P-0001-0000"] if self.plan_calls >= 3 else []
        self.planner_decisions.publish(record)
        return response

    def _scout(self, handle):
        self.goals.append(handle.request)
        if self.abort:  # the server gave up: the client gets a default Result (outcome 0 == SUCCEEDED)
            handle.abort()
            return ExecuteScout.Result()
        delta = CellDelta()
        delta.header.frame_id, delta.site_id, delta.resolution_m = "map", "TST", RES
        delta.origin.x, delta.origin.y = ORIGIN
        if self.blocked_on_route:  # cell (30, 35): centre (22, 2), on plan v1's outbound leg
            delta.cells = [CellState(iy=30, ix=35, state=1, speed_factor=0.0, evidence_id="scout-run-P-0001-0000")]
        else:  # an obstacle far from the route
            delta.cells = [CellState(iy=55, ix=5, state=1, speed_factor=0.0, evidence_id="scout-run-P-0001-0000")]
        if self.publish_known:
            self.known.publish(delta)
        handle.succeed()
        result = ExecuteScout.Result()
        result.outcome, result.evidence_ids = self.outcome, [] if self.empty else ["scout-run-P-0001-0000"]
        return result

    def propose(self, plan_id):
        record = DecisionRecord()
        record.decision_id, record.context = f"prop-{plan_id}-v1", "robot_task_proposal"
        record.chosen = f"{plan_id}-c1"
        record.assumptions_json = json.dumps({"plan_id": plan_id, "survey_area": [[10, -10], [50, -10], [50, 14],
                                                                                  [10, 14]]})
        self.proposals.publish(record)

    def until(self, predicate, timeout=15.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.01)
            if predicate():
                return True
        raise AssertionError("condition not reached")

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def contexts(rig):
    return [d.context for d in rig.decisions]


def test_an_obstacle_on_the_route_gives_plan_v2_only_with_the_scout_evidence_applied(ros):
    rig = Rig(blocked_on_route=True)
    try:
        rig.until(lambda: rig.states and rig.states[-1].phase == MissionState.PRECURSOR)
        rig.propose("plan-TST-0001")
        rig.until(lambda: rig.states[-1].phase == MissionState.TRAVERSE)
        assert len(rig.goals) == 1 and rig.goals[0].vehicle_id == "scout_1"
        assert [(p.x, p.y) for p in rig.goals[0].corridor.points] == [(10, -10), (50, -10), (50, 14), (10, 14)]
        assert rig.plan_calls == 3  # v1, a replan without the evidence (rejected by the gate), the accepted v2
        assert rig.states[-1].active_plan_id == "plan-TST-0002"
        rig.until(lambda: "replan after precursor" in contexts(rig))  # events may trail the latched state
        names = contexts(rig)
        assert "robot_task_dispatch" in names and "replan after precursor" in names
        replan = next(d for d in rig.decisions if d.context == "replan after precursor")
        assert list(replan.evidence_ids) == ["scout-run-P-0001-0000"]
        assert list(replan.candidates) == ["plan-TST-0001", "plan-TST-0002"] and replan.chosen == "plan-TST-0002"
        assert json.loads(replan.assumptions_json)["blocked_cells_on_route"] == [[30, 35]]
    finally:
        rig.close()


def test_an_obstacle_off_the_route_keeps_plan_v1(ros):
    rig = Rig(blocked_on_route=False)
    try:
        rig.until(lambda: rig.states and rig.states[-1].phase == MissionState.PRECURSOR)
        rig.propose("plan-TST-0001")
        rig.until(lambda: rig.states[-1].phase == MissionState.TRAVERSE)
        assert rig.plan_calls == 1 and rig.states[-1].active_plan_id == "plan-TST-0001"
        rig.until(lambda: "precursor: route clear, plan kept" in contexts(rig))
    finally:
        rig.close()


INCOMPLETE = "precursor: survey incomplete, plan kept unverified"


def test_an_aborted_scout_goal_never_declares_the_route_clear(ros):
    rig = Rig(blocked_on_route=False, abort=True)
    try:
        rig.until(lambda: rig.states and rig.states[-1].phase == MissionState.PRECURSOR)
        rig.propose("plan-TST-0001")
        rig.until(lambda: INCOMPLETE in contexts(rig))
        assert "precursor: route clear, plan kept" not in contexts(rig)
        record = next(d for d in rig.decisions if d.context == INCOMPLETE)
        assumptions = json.loads(record.assumptions_json)
        assert assumptions["route_verified"] is False and assumptions["scout_status"] == "ABORTED"
        assert rig.plan_calls == 1 and rig.states[-1].active_plan_id == "plan-TST-0001"
        rig.until(lambda: rig.states[-1].phase == MissionState.PRECURSOR)
        assert rig.node._pre_state == "incomplete"  # no silent egress from a failed survey
    finally:
        rig.close()


def test_a_failed_scout_with_no_blocked_cell_on_the_route_is_not_a_clear_route(ros):
    rig = Rig(blocked_on_route=False, outcome=ExecuteScout.Result.FAILED)
    try:
        rig.until(lambda: rig.states and rig.states[-1].phase == MissionState.PRECURSOR)
        rig.propose("plan-TST-0001")
        rig.until(lambda: INCOMPLETE in contexts(rig))
        assert "precursor: route clear, plan kept" not in contexts(rig)
        assumptions = json.loads(next(d for d in rig.decisions if d.context == INCOMPLETE).assumptions_json)
        assert assumptions["scout_outcome"] == "FAILED" and assumptions["route_verified"] is False
    finally:
        rig.close()


def test_a_partial_scout_that_saw_a_blocked_cell_on_the_route_still_replans(ros):
    rig = Rig(blocked_on_route=True, outcome=ExecuteScout.Result.PARTIAL)
    try:
        rig.until(lambda: rig.states and rig.states[-1].phase == MissionState.PRECURSOR)
        rig.propose("plan-TST-0001")
        rig.until(lambda: "replan after precursor" in contexts(rig))
        assert rig.states[-1].active_plan_id == "plan-TST-0002" or rig.until(
            lambda: rig.states[-1].active_plan_id == "plan-TST-0002")
    finally:
        rig.close()


def test_succeeded_scout_with_empty_evidence_holds_precursor(ros):
    rig = Rig(blocked_on_route=False, empty=True)
    try:
        rig.until(lambda: rig.states and rig.states[-1].phase == MissionState.PRECURSOR)
        rig.propose('plan-TST-0001')
        rig.until(lambda: INCOMPLETE in contexts(rig))
        assert rig.node.phase == MissionState.PRECURSOR and rig.node._pre_state == 'incomplete'
        assert 'precursor: route clear, plan kept' not in contexts(rig)
    finally:
        rig.close()


def test_missing_cell_store_evidence_never_means_clear_route(ros):
    rig = Rig(blocked_on_route=False, publish_known=False)
    try:
        rig.until(lambda: rig.states and rig.states[-1].phase == MissionState.PRECURSOR)
        rig.propose('plan-TST-0001')
        rig.until(lambda: rig.node._pre_state == 'settling')
        rig.node._scout_since = time.monotonic()-6
        rig.until(lambda: INCOMPLETE in contexts(rig))
        assert rig.node.phase == MissionState.PRECURSOR and rig.node._pre_state == 'incomplete'
        assert 'precursor: route clear, plan kept' not in contexts(rig)
        details = json.loads(next(d for d in rig.decisions if d.context == INCOMPLETE).assumptions_json)
        assert details['missing_count'] == 1
    finally:
        rig.close()


@pytest.mark.parametrize('callback', ['_on_scout_goal', '_on_scout_result'])
def test_scout_transport_exception_holds_precursor_without_crashing(ros, callback):
    rig = Rig(blocked_on_route=False)
    try:
        rig.until(lambda: rig.states and rig.states[-1].phase == MissionState.PRECURSOR)
        rig.node._pre_state = 'flying'
        future = Future();future.set_exception(RuntimeError('transport unavailable'))
        getattr(rig.node,callback)(future)
        rig.until(lambda: INCOMPLETE in contexts(rig))
        assert rig.node._pre_state == 'incomplete' and rig.node.phase == MissionState.PRECURSOR
        assert 'precursor: route clear, plan kept' not in contexts(rig)
    finally:
        rig.close()


def test_late_scout_result_cannot_override_an_emergency_phase(ros):
    rig = Rig(blocked_on_route=False)
    try:
        rig.until(lambda: rig.states and rig.states[-1].phase == MissionState.PRECURSOR)
        rig.node._pre_state = 'flying';rig.node.phase = MissionState.CONTINGENCY
        future = Future();future.set_exception(RuntimeError('late transport result'))
        rig.node._on_scout_result(future)
        assert rig.node.phase == MissionState.CONTINGENCY and rig.node._pre_state == 'flying'
        assert 'precursor: route clear, plan kept' not in contexts(rig)
    finally:
        rig.close()
