"""EVA planning service (proje.md §8.4 `planner_server`; D011).

``/redline/plan_eva`` (PlanEva): orienteering over the site's candidate targets with the
PET validity check, three Pareto routes (SCIENCE / SAFE / FAST) and, for up to 12
candidates, an exact reference with the heuristic's optimality gap. The requested route is
returned and published as ``/redline/plan`` (EVAPlan, transient-local) together with a
``/redline/decisions`` DecisionRecord naming the alternatives and why they were not chosen.

With several crew members the route is planned for the one with the highest nominal
metabolic power: the suit is sized at the same design point for everyone, so that member
has the smallest margins on any shared route. Logic lives in redline_core.
"""
from __future__ import annotations

import json
import math
from dataclasses import replace

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from redline_core.eva_plan import assemble_plan
from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.orienteering import OBJECTIVES, Candidate, RoutePlanner
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid
from redline_core.science_value import load_science
from redline_core.cells import delta_updates
from redline_msgs.msg import CellDelta, DecisionRecord, EVAPlan, PlanLeg, Station
from redline_msgs.srv import PlanEva

SERVICE = "/redline/plan_eva"
PLAN_TOPIC = "/redline/plan"
DELTA_TOPIC = "/redline/cells/delta"
DECISION_TOPIC = "/redline/decisions"
MAP_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
EVENT_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)


def load_targets(path: str, site_id: str, npz_sha256: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        record = json.load(handle)
    if record.get("site_id") != site_id:
        raise ValueError(f"targets are for site {record.get('site_id')!r}, not {site_id!r}")
    if record.get("planning_grid", {}).get("npz_sha256") != npz_sha256:
        raise ValueError("targets were derived on a different planning grid (cells would not align)")
    return record["targets"]


class PlannerServerNode(Node):
    def __init__(self, **kwargs):
        super().__init__("planner_server", **kwargs)
        names = ("planning_grid", "crew_file", "suit_file", "eva_file", "science_file", "targets_file")
        paths = {n: str(self.declare_parameter(n, "").value) for n in names}
        self.floor_fraction = float(self.declare_parameter("value_floor_fraction", 0.7).value)
        if not all(paths.values()):
            raise ValueError(f"parameters {names} are required")
        grid, meta = load_planning_grid(paths["planning_grid"])
        self.walk, self.suit = load_models(paths["suit_file"])
        self.crew = load_crew(paths["crew_file"])
        self.eva = load_eva(paths["eva_file"])
        crew_ids = [c for c in self.declare_parameter("crew_ids", [""]).value if c]
        if crew_ids:  # D015: the scenario crew list overrides eva.yaml
            self.eva = replace(self.eva, crew_ids=tuple(crew_ids))
        self.model = ReturnFieldModel(grid, self.walk, self.suit, self.crew, self.eva)
        self.science = load_science(paths["science_file"])
        if self.science.site_id != self.eva.site_id:
            raise ValueError("science model and EVA config name different sites")
        self.targets = {t["target_id"]: t for t in load_targets(paths["targets_file"], self.eva.site_id,
                                                                meta["npz_sha256"])}
        self.grid_sha = meta["npz_sha256"]
        self.version = 0
        self.applied_evidence: set[str] = set()  # D015: evidence behind the current cell states
        self._plan_pub = self.create_publisher(EVAPlan, PLAN_TOPIC, MAP_QOS)
        self._decision_pub = self.create_publisher(DecisionRecord, DECISION_TOPIC, EVENT_QOS)
        self.create_service(PlanEva, SERVICE, self._on_plan)
        self.create_subscription(CellDelta, DELTA_TOPIC, self._on_delta, EVENT_QOS)
        self.get_logger().info(f"{len(self.targets)} candidate targets, habitat {self.model.habitat_cell}")

    def _on_delta(self, delta: CellDelta) -> None:
        """Observed cells (D015): a replan sees them; the evidence ids go into the next DecisionRecord."""
        grid = self.model.grid
        try:
            if delta.header.frame_id != "map" or delta.site_id != self.eva.site_id:
                raise ValueError(f"delta for frame {delta.header.frame_id!r}, site {delta.site_id!r}")
            if (delta.resolution_m != np.float32(grid.resolution_m) or
                    (delta.origin.x, delta.origin.y) != tuple(float(v) for v in grid.origin_xy)):
                raise ValueError("delta geometry differs from the planning grid")
            self.model.apply_updates(delta_updates([(c.iy, c.ix, c.state, c.speed_factor, c.evidence_id)
                                                    for c in delta.cells]))
        except ValueError as error:
            self.get_logger().warning(f"cell delta rejected: {error}")
            return
        self.applied_evidence.update(c.evidence_id for c in delta.cells if c.evidence_id)

    def _fail(self, response, message):
        response.success, response.message = False, message
        self.get_logger().warning(f"PlanEva rejected: {message}")
        return response

    def _on_plan(self, request: PlanEva.Request, response: PlanEva.Response) -> PlanEva.Response:
        if request.site_id != self.eva.site_id:
            return self._fail(response, f"site {request.site_id!r} is not {self.eva.site_id!r}")
        objective = request.objective.upper()
        if objective not in OBJECTIVES:
            return self._fail(response, f"objective must be one of {OBJECTIVES}")
        crew_ids = list(request.crew_ids) or list(self.eva.crew_ids)
        unknown = [c for c in crew_ids if c not in self.model.crew]
        if unknown:
            return self._fail(response, f"unknown crew ids {unknown}")
        if not (math.isfinite(request.max_duration_min) and request.max_duration_min > 0):
            return self._fail(response, "max_duration_min must be positive")
        ids = list(request.candidate_target_ids) or sorted(self.targets)
        missing = [t for t in ids if t not in self.targets]
        if missing:
            return self._fail(response, f"unknown target ids {missing}")
        planning_crew = max(crew_ids, key=lambda c: self.model.nominal_rates(c).o2_kg_s)
        member = self.model.crew[planning_crew]
        if self.model.dirty:
            self.model.recompute()
        unreachable = [t for t in ids if not math.isfinite(self.model.field.time_s[tuple(self.targets[t]["cell"])])]
        ids = [t for t in ids if t not in unreachable]
        if not ids:
            return self._fail(response, f"no reachable candidate (unreachable: {unreachable})")
        self._unreachable = unreachable
        candidates = [Candidate(t, tuple(self.targets[t]["cell"]), self.targets[t]["science_class"],
                                60.0 * float(self.targets[t]["service_min"]), tuple(self.targets[t]["tasks"]))
                      for t in ids]
        try:
            planner = RoutePlanner(self.model.terrain, self.model.field, self.model.habitat_cell, candidates,
                                   self.science, self.science.prior, member, self.suit, self.walk,
                                   self.model.start_resources(planning_crew), self.model.reserve,
                                   60.0 * request.max_duration_min, z=self.eva.z_eps,
                                   sigma_theta=self.eva.sigma_theta, value_floor_fraction=self.floor_fraction)
            pareto = planner.pareto()
            route = pareto[objective]["route"]
            plan = assemble_plan(planner, route, objective, self.model.terrain, self.model.field, self.model.grid,
                                 self.model.habitat_cell)
        except ValueError as error:
            return self._fail(response, str(error))
        if not route.order:
            return self._fail(response, "no valid route visits any candidate within the limits")
        self.version += 1
        plan_id = f"plan-{self.eva.site_id}-{self.version:04d}"
        stamp = self.get_clock().now().to_msg()
        message = self._plan_message(plan_id, stamp, crew_ids, plan, request.max_duration_min)
        decision = self._decision_message(plan_id, stamp, objective, pareto, ids,
                                          [st.target_id for st in plan.stations], planning_crew)
        message.decision_id = decision.decision_id
        self._plan_pub.publish(message)
        self._decision_pub.publish(decision)
        response.success = True
        response.message = (f"{objective}: {len(route.order)} stations, {route.value_bits:.3f} bits, "
                             f"{route.duration_s / 60.0:.1f} min, tightest margin {route.min_margin_s / 60.0:.1f} min")
        response.plan = message
        return response

    def _plan_message(self, plan_id, stamp, crew_ids, plan, horizon_min) -> EVAPlan:
        message = EVAPlan()
        message.header.stamp, message.header.frame_id = stamp, "map"
        message.plan_id, message.version, message.site_id = plan_id, self.version, self.eva.site_id
        message.crew_ids = list(crew_ids)
        names = {"HAB": "HAB"}
        for k, s in enumerate(plan.stations):
            names[s.target_id] = f"S{k + 1}"
            station = Station()
            station.station_id, station.target_id = names[s.target_id], s.target_id
            station.position.x, station.position.y, station.position.z = s.xyz
            station.service_min = s.service_s / 60.0
            station.tasks = list(s.tasks)
            station.science_value = s.marginal_value_bits
            station.window_open_pet_min = s.window_open_s / 60.0
            # An open-ended window closes with the plan horizon (no inf over rosbridge).
            station.window_close_pet_min = min(s.window_close_s / 60.0, horizon_min)
            message.stations.append(station)
        for leg in plan.legs:
            item = PlanLeg()
            item.from_id, item.to_id = names[leg.from_id], names[leg.to_id]
            item.duration_min, item.duration_sigma_min = leg.duration_s / 60.0, leg.sigma_s / 60.0
            item.o2_kg, item.water_kg, item.battery_wh = leg.o2_kg, leg.water_kg, leg.battery_wh
            item.return_margin_min = leg.return_margin_s / 60.0
            message.legs.append(item)
        message.route.header = message.header
        points = plan.path_xyz
        for k, (x, y, z) in enumerate(points):
            pose = PoseStamped()
            pose.header = message.header
            pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = float(x), float(y), float(z)
            nx, ny = (points[min(k + 1, len(points) - 1)] - points[max(k - 1, 0)])[:2]
            yaw = math.atan2(ny, nx) if (nx or ny) else 0.0
            pose.pose.orientation.z, pose.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
            message.route.poses.append(pose)
        message.total_duration_min = plan.total_duration_s / 60.0
        return message

    def _decision_message(self, plan_id, stamp, objective, pareto, ids, chosen, planning_crew) -> DecisionRecord:
        record = DecisionRecord()
        record.header.stamp, record.header.frame_id = stamp, "map"
        record.decision_id = f"dec-{plan_id}"
        record.context = f"PlanEva objective={objective}"
        record.candidates = list(ids)
        record.chosen = ",".join(chosen)
        reasons = []
        for name, entry in pareto.items():
            if name == objective:
                continue
            alt = entry["route"]
            reasons.append(f"{name}: {len(alt.order)} stations, {alt.value_bits:.3f} bits, "
                           f"{alt.duration_s / 60.0:.1f} min, margin {alt.min_margin_s / 60.0:.1f} min "
                           f"(objective {objective} requested)")
        reasons += [f"{t}: not in the {objective} route" for t in ids if t not in chosen]
        reasons += [f"{t}: unreachable after observed obstacles" for t in getattr(self, "_unreachable", [])]
        record.rejected_reasons = reasons
        record.evidence_ids = sorted(self.applied_evidence)
        record.assumptions_json = json.dumps({
            "planning_crew": planning_crew, "value_floor_bits": pareto[objective]["floor_bits"],
            "gaps": {k: v["gap"] for k, v in pareto.items()},
            "exact_reference": {k: v["exact"] is not None for k, v in pareto.items()},
            "planning_grid_sha256": self.grid_sha, "decisions": ["D008", "D010", "D011", "D015"],
            "applied_evidence_ids": sorted(self.applied_evidence),
            "status": "SCENARIO",
        })
        record.model_version = "redline_core orienteering/science_value (D011)"
        return record


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PlannerServerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
