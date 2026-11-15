"""scout_stub over real DDS (D015): SIMULATED scout survey from SCENARIO truth, frozen action contract."""
import json
import time

import numpy as np
import pytest
import rclpy
from geometry_msgs.msg import Point32, Polygon
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter

from redline_core.grid import Grid
from redline_core.planning import save_planning_grid
from redline_core.truth import Obstacle, blocked_cells, scenario_world, survey_evidence, write_truth
from redline_env.scout_stub import EVIDENCE_QOS, EVIDENCE_TOPIC, MISSION_QOS, SCOUT_ACTION, SURVEY_ACTION, ScoutStubNode
from redline_msgs.action import ExecuteScout, SurveyArea
from redline_msgs.msg import EvidenceRecord, MissionState, Provenance

SQUARE = [(20.0, 20.0), (110.0, 20.0), (110.0, 60.0), (20.0, 60.0)]


@pytest.fixture
def files(tmp_path):
    shape = (20, 30)
    layers = {"z_m": np.zeros(shape), "slope_deg": np.zeros(shape), "slope_sigma_deg": np.full(shape, 0.5),
              "relief_m": np.zeros(shape), "wall_slope_deg": np.zeros(shape)}
    grid = Grid((0.0, 0.0), 4.0, shape[1], shape[0], layers)
    save_planning_grid(tmp_path / "grid", grid, {"status": "SIMULATED", "site_id": "TST", "note": "flat test grid"})
    world = scenario_world(grid, "TST", seed=4, k=0.0, d_range_m=(0.3, 3.0),
                           obstacles=[Obstacle("O1", 42.0, 42.0, 6.0)])
    write_truth(world, tmp_path / "scenario_rocks_4.json")
    return tmp_path, grid, world


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def polygon(points):
    return Polygon(points=[Point32(x=x, y=y, z=0.0) for x, y in points])


class Rig:
    def __init__(self, files, phase=MissionState.PRECURSOR):
        path, self.grid, self.world = files
        self.node = ScoutStubNode(parameter_overrides=[
            Parameter("truth_file", value=str(path / "scenario_rocks_4.json")),
            Parameter("planning_grid", value=str(path / "grid.npz")),
            Parameter("home_xy", value=[2.0, 2.0]), Parameter("time_scale", value=500.0)])
        self.probe = rclpy.create_node("probe")
        self.phase = phase
        self.mission = self.probe.create_publisher(MissionState, "/redline/mission/state", MISSION_QOS)
        self.mission_timer = self.probe.create_timer(0.1, self.publish_phase)
        self.records = []
        self.probe.create_subscription(EvidenceRecord, EVIDENCE_TOPIC, self.records.append, EVIDENCE_QOS)
        self.scout = ActionClient(self.probe, ExecuteScout, SCOUT_ACTION)
        self.survey = ActionClient(self.probe, SurveyArea, SURVEY_ACTION)
        self.executor = MultiThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)
        assert self.until(lambda: self.scout.server_is_ready() and self.survey.server_is_ready() and
                          (self.node._mission_phase == phase if phase is not None else True))

    def publish_phase(self):
        if self.phase is not None:
            message = MissionState();message.phase = self.phase
            self.mission.publish(message)

    def until(self, predicate, timeout=10.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.01)
            if predicate():
                return True
        return False

    def send(self, client, goal, feedback=None):
        future = client.send_goal_async(goal, feedback_callback=feedback)
        assert self.until(future.done)
        return future.result()

    def result(self, handle):
        future = handle.get_result_async()
        assert self.until(future.done, 20.0)
        return future.result().result

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def scout_goal(request_id="rq-1", vehicle="scout_1", points=SQUARE):
    goal = ExecuteScout.Goal()
    goal.request_id, goal.vehicle_id, goal.corridor = request_id, vehicle, polygon(points)
    goal.altitude_m = 20.0
    return goal


def test_a_scout_survey_reports_phases_and_simulated_evidence_from_the_truth(ros, files):
    rig = Rig(files)
    phases = []
    try:
        handle = rig.send(rig.scout, scout_goal(), lambda f: phases.append(f.feedback.phase))
        assert handle.accepted
        result = rig.result(handle)
        assert result.outcome == ExecuteScout.Result.SUCCEEDED and result.flight_s > 0 and result.battery_used_wh > 0
        assert [p for k, p in enumerate(phases) if k == 0 or p != phases[k - 1]] == [
            "PREFLIGHT", "TAKEOFF", "TRANSIT", "SURVEY", "RETURN", "LANDING"]
        assert rig.until(lambda: len(rig.records) == len(result.evidence_ids))
        assert {r.evidence_id for r in rig.records} == set(result.evidence_ids)
        assert all(r.provenance.status == Provenance.SIMULATED and r.source == "scout_stub" for r in rig.records)
        blocked = {rig.grid.cell_index(r.pose.pose.position.x, r.pose.pose.position.y) for r in rig.records
                   if not json.loads(r.summary_json)["cell_observation"].get("passable", True)}
        expected = {rig.grid.cell_index(x, y) for x, y, _, p in survey_evidence(
            rig.world, rig.grid, SQUARE, spacing_m=8.0, detection_limit_m=1.0, d_block_m=2.0) if not p}
        assert blocked == expected == blocked_cells(rig.world, rig.grid, 2.0)
    finally:
        rig.close()


def test_wrong_vehicle_duplicate_request_and_empty_area_are_rejected(ros, files):
    rig = Rig(files)
    try:
        assert not rig.send(rig.scout, scout_goal(vehicle="rover_1")).accepted
        first = rig.send(rig.scout, scout_goal("rq-dup"))
        assert first.accepted
        rig.result(first)
        assert not rig.send(rig.scout, scout_goal("rq-dup")).accepted  # repeated command id
        assert not rig.send(rig.scout, scout_goal("rq-empty", points=[(1.0, 1.0), (2.0, 2.0)])).accepted
        goal = SurveyArea.Goal()
        goal.request_id, goal.vehicle_id, goal.area, goal.purpose = "rq-area", "scout_1", polygon(SQUARE), "corridor"
        handle = rig.send(rig.survey, goal)
        assert handle.accepted
        result = rig.result(handle)
        assert result.outcome == SurveyArea.Result.SUCCEEDED and result.covered_fraction == pytest.approx(1.0)
    finally:
        rig.close()


def test_a_cancelled_flight_ends_canceled(ros, files):
    path, grid, world = files
    rig = Rig(files)
    rig.node.time_scale = 5.0  # slow enough to cancel in flight
    try:
        handle = rig.send(rig.scout, scout_goal("rq-cancel"))
        assert handle.accepted
        rig.until(lambda: False, 0.3)
        cancel = handle.cancel_goal_async()
        assert rig.until(cancel.done)
        assert rig.result(handle).outcome == ExecuteScout.Result.CANCELED
    finally:
        rig.close()


def test_refuses_to_start_when_a_gazebo_scout_publishes_odometry(ros, files):
    path, _, _ = files
    probe = rclpy.create_node("gazebo_scout")
    probe.create_publisher(Odometry, "/scout_1/odom", 10)
    time.sleep(0.5)
    try:
        with pytest.raises(RuntimeError, match="scout_1"):
            ScoutStubNode(parameter_overrides=[Parameter("truth_file", value=str(path / "scenario_rocks_4.json")),
                                               Parameter("planning_grid", value=str(path / "grid.npz"))])
    finally:
        probe.destroy_node()


@pytest.mark.parametrize("phase", [None, MissionState.BRIEFING, MissionState.TRAVERSE, MissionState.CONTINGENCY])
def test_only_a_fresh_precursor_may_accept_a_scout_request(ros, files, phase):
    rig = Rig(files, phase=phase)
    try:
        assert not rig.send(rig.scout, scout_goal()).accepted
        assert rig.records == []
    finally:
        rig.close()


def test_a_stale_precursor_is_rejected_and_cannot_generate_evidence(ros, files):
    rig = Rig(files)
    try:
        rig.mission_timer.cancel()
        rig.node._mission_receipt = time.monotonic()-4
        assert not rig.send(rig.scout, scout_goal()).accepted
        assert rig.records == []
    finally:
        rig.close()


def test_phase_change_during_flight_aborts_before_survey_evidence(ros, files):
    rig = Rig(files)
    rig.node.time_scale = 5.0
    try:
        handle = rig.send(rig.scout, scout_goal())
        assert handle.accepted
        rig.phase = MissionState.CONTINGENCY
        assert rig.until(lambda: rig.node._mission_phase == MissionState.CONTINGENCY)
        result = rig.result(handle)
        assert result.outcome == ExecuteScout.Result.FAILED
        assert not result.evidence_ids and not rig.records
    finally:
        rig.close()


def test_only_one_active_scout_survey_is_accepted(ros, files):
    rig = Rig(files)
    rig.node.time_scale = 5.0
    try:
        first = rig.send(rig.scout, scout_goal('busy-first'))
        assert first.accepted
        assert not rig.send(rig.scout, scout_goal('busy-second')).accepted
        first.cancel_goal_async()
        assert rig.result(first).outcome == ExecuteScout.Result.CANCELED
    finally:
        rig.close()
