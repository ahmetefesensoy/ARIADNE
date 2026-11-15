"""Robot task proposals from the value of information (proje.md §8.3 `voi_tasker`, §7.11; D011, D015).

On every new EVAPlan the node rebuilds the plan's route with the same inputs as planner_server
(planning grid, crew, suit, EVA, science model, targets), applies the latched known cells, ranks
the VOI candidates of redline_core.voi in a worker thread (BXW: ~17 s for 1461 candidates) and
publishes one DecisionRecord on ``/redline/robot_tasks/proposed`` (latched):

- ``candidates``: the top K as ``redline.robot_task_proposal.v1`` JSON, one per candidate, mapped
  1:1 to a SurveyArea goal (vehicle, footprint polygon in ``map``) plus the VOI terms;
- ``chosen``: the best candidate id; ``evidence_ids``: observations behind the cell states;
- ``assumptions_json``: plan id and version, VOI parameters (SCENARIO, config/voi.yaml), the
  survey area and the compute time.

Survey area (D015, corridor policy): the crew walks the planned path up to a candidate, so an
obstacle anywhere on that stretch matters. The area is the bounding box of the top-K footprints
plus, for each candidate, the cells of its nearest planned walk from the walk's start to the
candidate, padded by the footprint. The first S4 run used footprints only and missed an obstacle
4 m outside the box; this is the council's corridor recommendation, adopted for every scenario.

Values are SCENARIO estimates. Proposals are not commands: mission_manager decides and records a
separate dispatch decision.
"""
from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import replace

import numpy as np
import rclpy
import yaml
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from redline_core.cells import delta_updates
from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.orienteering import Candidate, RoutePlanner
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid
from redline_core.science_value import load_science
from redline_core.voi import VoiEstimator
from redline_msgs.msg import CellDelta, DecisionRecord, EVAPlan

PROPOSAL_TOPIC = "/redline/robot_tasks/proposed"
PROPOSAL_SCHEMA = "redline.robot_task_proposal.v1"
KNOWN_TOPIC = "/redline/cells/known"
PROPOSAL_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                          durability=DurabilityPolicy.TRANSIENT_LOCAL)
LATCHED = PROPOSAL_QOS
_VOI_KEYS = {"provenance_status", "note", "obstacle_density_per_km2", "sight_m", "corridor_m", "window_m",
             "lattice_m", "footprint_m", "top_k"}


def load_voi(path: str) -> dict:
    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    unknown = set(data) - _VOI_KEYS
    if unknown:
        raise ValueError(f"{path}: unknown keys {sorted(unknown)}")
    if data.get("provenance_status") != "SCENARIO":
        raise ValueError(f"{path}: VOI parameters must be SCENARIO")
    return data


class VoiTaskerNode(Node):
    def __init__(self, **kwargs):
        super().__init__("voi_tasker", **kwargs)
        names = ("planning_grid", "crew_file", "suit_file", "eva_file", "science_file", "targets_file", "voi_file")
        paths = {n: str(self.declare_parameter(n, "").value) for n in names}
        if not all(paths.values()):
            raise ValueError(f"parameters {names} are required")
        crew_ids = [c for c in self.declare_parameter("crew_ids", [""]).value if c]
        self.vehicle_id = str(self.declare_parameter("vehicle_id", "scout_1").value)
        self.robot_speed = float(self.declare_parameter("robot_speed_m_s", 5.0).value)
        self.inspect_s = float(self.declare_parameter("inspect_s", 60.0).value)
        self.max_duration_min = float(self.declare_parameter("max_duration_min", 300.0).value)
        self.voi = load_voi(paths["voi_file"])
        grid, meta = load_planning_grid(paths["planning_grid"])
        self.walk, self.suit = load_models(paths["suit_file"])
        self.crew = load_crew(paths["crew_file"])
        self.eva = load_eva(paths["eva_file"])
        if crew_ids:
            self.eva = replace(self.eva, crew_ids=tuple(crew_ids))
        self.model = ReturnFieldModel(grid, self.walk, self.suit, self.crew, self.eva)
        self.science = load_science(paths["science_file"])
        record = json.load(open(paths["targets_file"], encoding="utf-8"))
        if record.get("planning_grid", {}).get("npz_sha256") != meta["npz_sha256"]:
            raise ValueError("targets were derived on a different planning grid")
        self.targets = {t["target_id"]: t for t in record["targets"]}
        self.evidence: set[str] = set()
        self._lock = threading.Lock()
        self._busy = False
        self.counts = {"plans": 0, "proposals": 0, "failed": 0}
        self._pub = self.create_publisher(DecisionRecord, PROPOSAL_TOPIC, PROPOSAL_QOS)
        self.create_subscription(EVAPlan, "/redline/plan", self._on_plan, LATCHED)
        self.create_subscription(CellDelta, KNOWN_TOPIC, self._on_known, LATCHED)

    def _on_known(self, delta: CellDelta) -> None:
        if delta.header.frame_id != "map" or delta.site_id != self.eva.site_id:
            return
        with self._lock:
            self.model.apply_updates(delta_updates([(c.iy, c.ix, c.state, c.speed_factor, c.evidence_id)
                                                    for c in delta.cells]))
            self.evidence.update(c.evidence_id for c in delta.cells if c.evidence_id)

    def _on_plan(self, plan: EVAPlan) -> None:
        self.counts["plans"] += 1
        if self._busy:
            self.get_logger().warning("a VOI ranking is still running; this plan waits for the next one")
            return
        self._busy = True
        threading.Thread(target=self._rank, args=(plan,), daemon=True).start()

    def _rank(self, plan: EVAPlan) -> None:
        started = time.perf_counter()
        try:
            with self._lock:
                if self.model.dirty:
                    self.model.recompute()
                ids = [s.target_id for s in plan.stations]
                candidates = [Candidate(t, tuple(self.targets[t]["cell"]), self.targets[t]["science_class"],
                                        60.0 * float(self.targets[t]["service_min"]), tuple(self.targets[t]["tasks"]))
                              for t in ids]
                crew_ids = list(plan.crew_ids) or list(self.eva.crew_ids)
                planning_crew = max(crew_ids, key=lambda c: self.model.nominal_rates(c).o2_kg_s)
                planner = RoutePlanner(self.model.terrain, self.model.field, self.model.habitat_cell, candidates,
                                       self.science, self.science.prior, self.model.crew[planning_crew], self.suit,
                                       self.walk, self.model.start_resources(planning_crew), self.model.reserve,
                                       60.0 * self.max_duration_min, z=self.eva.z_eps,
                                       sigma_theta=self.eva.sigma_theta)
                route = planner.evaluate(list(range(len(candidates))))
                v = self.voi
                estimator = VoiEstimator(self.model, planner, route,
                                         corridor_m=float(v["corridor_m"]), window_m=float(v["window_m"]),
                                         lattice_m=float(v["lattice_m"]), footprint_m=float(v["footprint_m"]),
                                         obstacle_density_per_km2=float(v["obstacle_density_per_km2"]),
                                         sight_m=float(v["sight_m"]), robot_speed_m_s=self.robot_speed,
                                         inspect_s=self.inspect_s)
                total = len(estimator.candidate_cells())
                ranked = estimator.rank(int(v["top_k"]))
                evidence = sorted(self.evidence)
                corridor, starts = self._corridor_points(estimator, ranked)
            self._publish(plan, ranked, total, evidence, time.perf_counter() - started, corridor, starts)
        except (ValueError, KeyError) as error:
            self.counts["failed"] += 1
            self.get_logger().error(f"VOI ranking for {plan.plan_id} failed: {error}")
        finally:
            self._busy = False

    def _corridor_points(self, estimator: VoiEstimator, ranked):
        """Cell centres of each candidate's nearest planned walk from its start to the candidate,
        and the walk start per candidate (None when no walk is within corridor_m)."""
        grid = self.model.grid
        reach = float(self.voi["corridor_m"])
        points, starts = [], []
        for c in ranked:
            best = None
            for path in estimator.paths:
                xy = np.array([grid.cell_center(*cell) for cell in path.cells])
                d = np.hypot(xy[:, 0] - c.xy[0], xy[:, 1] - c.xy[1])
                k = int(np.argmin(d))
                if d[k] <= reach and (best is None or d[k] < best[0]):
                    best = (d[k], xy[:k + 1])
            if best is not None:
                points.extend((float(x), float(y)) for x, y in best[1])
                starts.append([float(best[1][0][0]), float(best[1][0][1])])
            else:
                starts.append(None)
        return points, starts

    def _publish(self, plan: EVAPlan, ranked, total: int, evidence: list[str], compute_s: float,
                 corridor: list[tuple[float, float]] = (), starts: list | None = None) -> None:
        half = float(self.voi["footprint_m"])
        items = []
        for rank, c in enumerate(ranked, start=1):
            x, y = (float(v) for v in c.xy)
            items.append({
                "schema": PROPOSAL_SCHEMA, "candidate_id": f"{plan.plan_id}-c{rank}", "rank": rank,
                "vehicle_id": self.vehicle_id, "cell": [int(c.cell[0]), int(c.cell[1])], "xy": [x, y],
                "area": [[x - half, y - half], [x + half, y - half], [x + half, y + half], [x - half, y + half]],
                "p_block": 1.0 - c.p_open, "voi_min": c.voi_s / 60.0, "legacy_voi_min": c.legacy_voi_s / 60.0,
                "margin_now_min": c.margin_now_s / 60.0, "margin_open_min": c.margin_open_s / 60.0,
                "margin_blocked_min": c.margin_blocked_s / 60.0, "margin_late_min": c.margin_late_s / 60.0,
                "robot_cost_s": c.robot_cost_s, "score": c.score,
                "corridor_start_xy": (starts or [None] * len(ranked))[rank - 1]})
        items = [{k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in i.items()}
                 for i in items]
        if items:
            xs = [p[0] for i in items for p in i["area"]] + [x + d for x, _ in corridor for d in (-half, half)]
            ys = [p[1] for i in items for p in i["area"]] + [y + d for _, y in corridor for d in (-half, half)]
            area = [[min(xs), min(ys)], [max(xs), min(ys)], [max(xs), max(ys)], [min(xs), max(ys)]]
        else:
            area = []
        record = DecisionRecord()
        record.header.stamp, record.header.frame_id = self.get_clock().now().to_msg(), "map"
        record.decision_id = f"prop-{plan.plan_id}-v{plan.version}"
        record.context = "robot_task_proposal"
        record.evidence_ids = evidence
        record.candidates = [json.dumps(i, sort_keys=True) for i in items]
        record.chosen = items[0]["candidate_id"] if items else ""
        record.rejected_reasons = [f"{total - len(items)} lower-scoring candidates not proposed"]
        record.assumptions_json = json.dumps({
            "status": "SCENARIO", "plan_id": plan.plan_id, "plan_version": plan.version,
            "voi": {k: self.voi[k] for k in sorted(self.voi) if k not in ("note", "provenance_status")},
            "candidates_evaluated": total, "compute_s": compute_s, "survey_area": area, "survey_policy": "corridor",
            "corridor_cells": len(corridor), "decisions": ["D011", "D015"]})
        record.model_version = "redline_core.voi (D015: late discovery, VOI >= 0)"
        self._pub.publish(record)
        self.counts["proposals"] += 1
        self.get_logger().info(f"{plan.plan_id}: {len(items)} proposals of {total} candidates in {compute_s:.1f} s")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VoiTaskerNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
