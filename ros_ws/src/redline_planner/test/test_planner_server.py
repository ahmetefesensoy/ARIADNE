"""planner_server over real DDS: PlanEva objectives, plan layout, decision record, rejections."""
import json

import numpy as np
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter

from redline_msgs.msg import DecisionRecord, EVAPlan
from redline_msgs.srv import PlanEva
from redline_planner.planner_server import DECISION_TOPIC, EVENT_QOS, MAP_QOS, PLAN_TOPIC, SERVICE, PlannerServerNode
from t5_fixtures import spin_until, write_inputs

SCIENCE = """provenance_status: SCENARIO
site_id: TST
question: test
hypotheses:
  - {id: H1, prior: 0.3333333333333333}
  - {id: H2, prior: 0.3333333333333333}
  - {id: H3, prior: 0.3333333333333334}
observation:
  ridge: {H1: 0.85, H2: 0.15, H3: 0.5}
  hollow: {H1: 0.85, H2: 0.15, H3: 0.5}
"""
# Habitat cell (30, 30) is at (2, 2) m; targets 40-80 m away on the flat test grid.
TARGETS = [("TST-T01", "ridge", (30, 45)), ("TST-T02", "hollow", (45, 30)),
           ("TST-T03", "ridge", (15, 30)), ("TST-T04", "hollow", (30, 12))]


@pytest.fixture
def paths(tmp_path):
    files = write_inputs(tmp_path)
    (tmp_path / "science.yaml").write_text(SCIENCE)
    sha = json.loads((tmp_path / "grid.json").read_text())["npz_sha256"]
    record = {"site_id": "TST", "planning_grid": {"npz_sha256": sha},
              "targets": [{"target_id": t, "science_class": c, "cell": list(cell), "service_min": 10.0,
                           "tasks": ["PHOTO", "LIBS"]} for t, c, cell in TARGETS]}
    (tmp_path / "targets.json").write_text(json.dumps(record))
    return {**files, "science_file": str(tmp_path / "science.yaml"), "targets_file": str(tmp_path / "targets.json")}


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


class Rig:
    def __init__(self, paths):
        self.node = PlannerServerNode(parameter_overrides=[Parameter(k, value=v) for k, v in paths.items()])
        self.probe = rclpy.create_node("probe")
        self.plans, self.decisions = [], []
        self.probe.create_subscription(EVAPlan, PLAN_TOPIC, self.plans.append, MAP_QOS)
        self.probe.create_subscription(DecisionRecord, DECISION_TOPIC, self.decisions.append, EVENT_QOS)
        self.client = self.probe.create_client(PlanEva, SERVICE)
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)
        assert spin_until(self.executor, self.client.service_is_ready, 5.0)

    def call(self, objective="SCIENCE", site="TST", targets=(), minutes=240.0):
        request = PlanEva.Request()
        request.site_id, request.objective, request.max_duration_min = site, objective, minutes
        request.crew_ids = ["EV1"]
        request.candidate_target_ids = list(targets)
        future = self.client.call_async(request)
        assert spin_until(self.executor, future.done, 60.0)
        return future.result()

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def test_plans_have_stations_legs_a_route_and_a_decision_record(ros, paths):
    rig = Rig(paths)
    try:
        science = rig.call("SCIENCE")
        assert science.success, science.message
        plan = science.plan
        assert plan.site_id == "TST" and plan.header.frame_id == "map" and plan.version == 1
        assert len(plan.stations) >= 2 and len(plan.legs) == len(plan.stations) + 1
        assert plan.legs[0].from_id == "HAB" and plan.legs[-1].to_id == "HAB"
        assert [s.station_id for s in plan.stations] == [f"S{k + 1}" for k in range(len(plan.stations))]
        assert all(s.science_value > 0 and s.service_min == 10.0 for s in plan.stations)
        assert all(np.isfinite(s.window_close_pet_min) for s in plan.stations)
        poses = [(p.pose.position.x, p.pose.position.y) for p in plan.route.poses]
        assert poses[0] == pytest.approx((2.0, 2.0)) and poses[-1] == pytest.approx((2.0, 2.0))
        assert plan.total_duration_min > sum(s.service_min for s in plan.stations)
        assert spin_until(rig.executor, lambda: rig.plans and rig.decisions, 5.0)
        decision = rig.decisions[-1]
        assert decision.decision_id == plan.decision_id == "dec-plan-TST-0001"
        assumptions = json.loads(decision.assumptions_json)
        assert set(assumptions["gaps"]) == {"SCIENCE", "SAFE", "FAST"} and assumptions["status"] == "SCENARIO"
        assert any(r.startswith("FAST:") for r in decision.rejected_reasons)

        fast = rig.call("FAST")
        assert fast.success and fast.plan.version == 2
        assert fast.plan.total_duration_min <= plan.total_duration_min + 1e-6
    finally:
        rig.close()


def test_rejects_bad_requests(ros, paths):
    rig = Rig(paths)
    try:
        assert not rig.call(site="BXW").success
        assert not rig.call(objective="FASTEST").success
        assert not rig.call(targets=["TST-T99"]).success
        assert not rig.call(minutes=0.0).success
        short = rig.call(minutes=1.0)
        assert not short.success and "no valid route" in short.message
        only = rig.call(targets=["TST-T02"])
        assert only.success and [s.target_id for s in only.plan.stations] == ["TST-T02"]
    finally:
        rig.close()


def test_refuses_targets_from_another_grid(ros, paths, tmp_path):
    record = json.loads((tmp_path / "targets.json").read_text())
    record["planning_grid"]["npz_sha256"] = "0" * 64
    (tmp_path / "targets.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="different planning grid"):
        PlannerServerNode(parameter_overrides=[Parameter(k, value=v) for k, v in paths.items()])


# --- D015: the planner sees observed obstacles and names the evidence it applied --------------
def test_a_replan_avoids_cells_blocked_by_evidence_and_records_the_evidence(ros, paths):
    from redline_core.cost_human import DETECTED
    from redline_msgs.msg import CellDelta, CellState
    from redline_planner.planner_server import DELTA_TOPIC
    from t5_fixtures import ORIGIN

    rig = Rig(paths)
    try:
        first = rig.call("SCIENCE", targets=("TST-T01", "TST-T02"))
        assert first.success and "TST-T01" in [s.target_id for s in first.plan.stations]
        ring = [(30 + dy, 45 + dx) for dy in range(-2, 3) for dx in range(-2, 3) if max(abs(dy), abs(dx)) == 2]
        delta = CellDelta()
        delta.header.frame_id, delta.site_id, delta.resolution_m = "map", "TST", 4.0
        delta.origin.x, delta.origin.y = ORIGIN
        delta.cells = [CellState(iy=iy, ix=ix, state=DETECTED, speed_factor=0.0, evidence_id="ev-ring")
                       for iy, ix in ring]
        publisher = rig.probe.create_publisher(CellDelta, DELTA_TOPIC, EVENT_QOS)
        assert spin_until(rig.executor, lambda: (publisher.publish(delta), "ev-ring" in rig.node.applied_evidence)[1],
                          5.0)
        second = rig.call("SCIENCE", targets=("TST-T01", "TST-T02"))
        assert second.success, second.message
        assert [s.target_id for s in second.plan.stations] == ["TST-T02"]  # T01 is walled in
        assert spin_until(rig.executor, lambda: len(rig.decisions) >= 2, 5.0)
        decision = rig.decisions[-1]
        assert list(decision.evidence_ids) == ["ev-ring"]
        assert json.loads(decision.assumptions_json)["applied_evidence_ids"] == ["ev-ring"]
    finally:
        rig.close()


def test_crew_ids_parameter_sets_the_planning_crew(ros, paths, tmp_path):
    (tmp_path / "crew.yaml").write_text("provenance_status: SCENARIO\ncrew:\n"
                                        "  EV1: {body_mass_kg: 75.0, load_mass_kg: 80.0, theta: 1.0}\n"
                                        "  EV2: {body_mass_kg: 68.0, load_mass_kg: 80.0, theta: 1.0}\n")
    node = PlannerServerNode(parameter_overrides=[Parameter(k, value=v) for k, v in paths.items()] +
                             [Parameter("crew_ids", value=["EV1", "EV2"])])
    try:
        assert node.eva.crew_ids == ("EV1", "EV2") and set(node.model.crew) == {"EV1", "EV2"}
    finally:
        node.destroy_node()
