"""voi_tasker over real DDS (proje.md §8.3, §7.11; D015): a plan in, a versioned robot task proposal out."""
import json
import time

import numpy as np
import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter

from redline_core.grid import Grid
from redline_core.planning import save_planning_grid
from redline_mission.voi_tasker import PROPOSAL_QOS, PROPOSAL_TOPIC, PROPOSAL_SCHEMA, VoiTaskerNode
from redline_msgs.msg import DecisionRecord, EVAPlan, Station

EVA = """provenance_status: SCENARIO
site_id: TST
crew_ids: [EV1]
habitat: {requested_xy_m: [0.0, 0.0], placement: nearest_in_largest_component}
reserve: {o2_kg: 0.1, co2_capacity_kg: 0.0, water_kg: 0.0, battery_wh: 0.0}
start: {minutes_above_reserve: 120.0}
lines: {terminate_threshold_min: 10.0, simplify_tolerance_m: 4.0, min_hole_area_m2: 0.0}
tile: {lo_min: -60.0, hi_min: 60.0, bit_depth: 8}
sigma_fallback_percentile: 95.0
"""
SCIENCE = """provenance_status: SCENARIO
site_id: TST
question: test
hypotheses:
  - {id: H1, prior: 0.5}
  - {id: H2, prior: 0.5}
observation:
  ridge: {H1: 0.9, H2: 0.1}
  hollow: {H1: 0.9, H2: 0.1}
"""
TARGETS = [("TST-T01", "ridge", (30, 45)), ("TST-T02", "hollow", (45, 30))]
VOI = "provenance_status: SCENARIO\nobstacle_density_per_km2: 1000.0\nsight_m: 10.0\ncorridor_m: 50.0\n" \
      "window_m: 200.0\nlattice_m: 12.0\nfootprint_m: 6.0\ntop_k: 3\n"


@pytest.fixture
def files(tmp_path):
    shape = (60, 60)
    layers = {"z_m": np.zeros(shape), "slope_deg": np.zeros(shape), "slope_sigma_deg": np.full(shape, 0.5),
              "relief_m": np.zeros(shape), "wall_slope_deg": np.zeros(shape)}
    save_planning_grid(tmp_path / "grid", Grid((-120.0, -120.0), 4.0, 60, 60, layers),
                       {"status": "SIMULATED", "site_id": "TST", "note": "synthetic flat test grid"})
    (tmp_path / "crew.yaml").write_text(
        "provenance_status: SCENARIO\ncrew:\n  EV1: {body_mass_kg: 75.0, load_mass_kg: 80.0, theta: 1.0}\n")
    (tmp_path / "suit.yaml").write_text("provenance_status: SCENARIO\nwalk: {}\nsuit: {}\n")
    (tmp_path / "eva.yaml").write_text(EVA)
    (tmp_path / "science.yaml").write_text(SCIENCE)
    (tmp_path / "voi.yaml").write_text(VOI)
    sha = json.loads((tmp_path / "grid.json").read_text())["npz_sha256"]
    (tmp_path / "targets.json").write_text(json.dumps({
        "site_id": "TST", "planning_grid": {"npz_sha256": sha},
        "targets": [{"target_id": t, "science_class": c, "cell": list(cell), "service_min": 10.0,
                     "tasks": ["PHOTO"]} for t, c, cell in TARGETS]}))
    names = ("planning_grid", "crew_file", "suit_file", "eva_file", "science_file", "targets_file", "voi_file")
    values = ("grid.npz", "crew.yaml", "suit.yaml", "eva.yaml", "science.yaml", "targets.json", "voi.yaml")
    return {n: str(tmp_path / v) for n, v in zip(names, values)}


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def plan_message():
    plan = EVAPlan()
    plan.header.frame_id, plan.plan_id, plan.version, plan.site_id = "map", "plan-TST-0001", 1, "TST"
    plan.total_duration_min = 90.0
    for k, (target, _, (iy, ix)) in enumerate(TARGETS):
        station = Station()
        station.station_id, station.target_id = f"S{k + 1}", target
        station.position.x, station.position.y = -120.0 + 4 * ix + 2, -120.0 + 4 * iy + 2
        station.window_close_pet_min = 240.0
        plan.stations.append(station)
    plan.route.poses = [PoseStamped()]
    return plan


def test_a_plan_gets_a_ranked_versioned_proposal_with_a_survey_area(ros, files):
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
    node = VoiTaskerNode(parameter_overrides=[Parameter(k, value=v) for k, v in files.items()])
    probe = rclpy.create_node("probe")
    proposals = []
    probe.create_subscription(DecisionRecord, PROPOSAL_TOPIC, proposals.append, PROPOSAL_QOS)
    latched = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
    publisher = probe.create_publisher(EVAPlan, "/redline/plan", latched)
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor.add_node(probe)
    try:
        publisher.publish(plan_message())
        end = time.monotonic() + 60.0
        while time.monotonic() < end and not proposals:
            executor.spin_once(timeout_sec=0.05)
        assert proposals, "no proposal within 60 s"
        record = proposals[-1]
        assert record.context == "robot_task_proposal" and record.decision_id.startswith("prop-plan-TST-0001")
        candidates = [json.loads(c) for c in record.candidates]
        assert len(candidates) == 3 and all(c["schema"] == PROPOSAL_SCHEMA for c in candidates)
        scores = [c["score"] for c in candidates]
        assert scores == sorted(scores, reverse=True) and all(c["voi_min"] >= 0 for c in candidates)
        assert record.chosen == candidates[0]["candidate_id"] and candidates[0]["vehicle_id"] == "scout_1"
        assumptions = json.loads(record.assumptions_json)
        assert assumptions["status"] == "SCENARIO" and assumptions["plan_id"] == "plan-TST-0001"
        area = assumptions["survey_area"]
        assert len(area) == 4 and all(len(p) == 2 for p in area)
        xs, ys = [p[0] for p in area], [p[1] for p in area]
        for c in candidates:  # every proposed footprint lies inside the survey area
            assert min(xs) <= c["xy"][0] <= max(xs) and min(ys) <= c["xy"][1] <= max(ys)
        # D015 corridor survey: the walk from the start of each candidate's nearest planned walk to
        # the candidate is surveyed too (S4 run 1 missed an obstacle on that stretch).
        assert assumptions["survey_policy"] == "corridor" and assumptions["corridor_cells"] > 0
        for c in candidates:
            start = c["corridor_start_xy"]
            assert start is not None and min(xs) <= start[0] <= max(xs) and min(ys) <= start[1] <= max(ys)
    finally:
        executor.shutdown()
        node.destroy_node()
        probe.destroy_node()
