"""SIMULATED stand-in for the scout drone (proje.md §5 ExecuteScout/SurveyArea, §18.2 stubs; D015).

There is no Gazebo scout yet, so this node implements the frozen actions for ``scout_1`` and
turns a survey into EvidenceRecords from the hidden SCENARIO truth (redline_core.truth): blocked
cells inside the area as ``cell_observation.v2`` obstacles, the rest as observed open ground.
Features smaller than ``detection_limit_m`` are not seen. Every record is SIMULATED and names
the stub as its source.

It never publishes TF, odometry or velocity commands, and it refuses to start while a real
``scout_1`` publishes ``/scout_1/odom``: one robot authority (AGENTS.md). Flight time is robot
time (distance / speed + survey path), shortened in wall time by ``time_scale``; the stub flies
only in PRECURSOR, while mission time is held, so FR-14 (drone ≥ 30 m from the crew) does not
apply. Outcomes follow the frozen codes; a repeated request id or another vehicle is rejected.
"""
from __future__ import annotations

import json
import math
import threading
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from redline_core.planning import load_planning_grid
from redline_core.truth import load_truth, survey_evidence
from redline_msgs.action import ExecuteScout, SurveyArea
from redline_msgs.msg import EvidenceRecord, MissionState, Provenance

EVIDENCE_TOPIC = "/redline/evidence"
SCOUT_ACTION = "/scout_1/execute_scout"
SURVEY_ACTION = "/scout_1/survey_area"
EVIDENCE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50, reliability=ReliabilityPolicy.RELIABLE,
                          durability=DurabilityPolicy.VOLATILE)
PHASES = ("PREFLIGHT", "TAKEOFF", "TRANSIT", "SURVEY", "RETURN", "LANDING")
MISSION_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)


class ScoutStubNode(Node):
    def __init__(self, **kwargs):
        super().__init__("scout_stub", **kwargs)
        truth_file = str(self.declare_parameter("truth_file", "").value)
        grid_path = str(self.declare_parameter("planning_grid", "").value)
        self.vehicle_id = str(self.declare_parameter("vehicle_id", "scout_1").value)
        self.speed_m_s = float(self.declare_parameter("speed_m_s", 5.0).value)
        self.spacing_m = float(self.declare_parameter("survey_spacing_m", 8.0).value)
        self.detection_limit_m = float(self.declare_parameter("detection_limit_m", 1.0).value)
        self.d_block_m = float(self.declare_parameter("d_block_m", 2.0).value)
        self.power_w = float(self.declare_parameter("power_w", 300.0).value)
        self.phase_s = float(self.declare_parameter("takeoff_landing_s", 30.0).value)
        self.time_scale = float(self.declare_parameter("time_scale", 1.0).value)
        self.mission_max_age_s = float(self.declare_parameter("mission_max_age_s", 3.0).value)
        home = list(self.declare_parameter("home_xy", [math.nan, math.nan]).value)
        if not (truth_file and grid_path):
            raise ValueError("truth_file and planning_grid parameters are required")
        if not all(math.isfinite(value) and value > 0 for value in (
                self.speed_m_s, self.spacing_m, self.detection_limit_m, self.d_block_m,
                self.power_w, self.phase_s, self.time_scale, self.mission_max_age_s)):
            raise ValueError("scout timing, sensing, power and mission freshness parameters must be finite and positive")
        for _ in range(20):  # one robot authority: a real scout_1 wins
            if self.count_publishers(f"/{self.vehicle_id}/odom") > 0:
                raise RuntimeError(f"a real {self.vehicle_id} publishes /{self.vehicle_id}/odom; the stub must not run")
            time.sleep(0.02)
        self.world = load_truth(truth_file)
        self.grid, meta = load_planning_grid(grid_path)
        self.home_xy = tuple(home) if all(math.isfinite(v) for v in home) else tuple(self.grid.cell_center(
            self.grid.height // 2, self.grid.width // 2))
        self.truth_name = truth_file.rsplit("/", 1)[-1]
        self.seen_requests: set[str] = set()
        self._lock = threading.Lock()
        self._busy = False
        self._mission_phase = None
        self._mission_receipt = -math.inf
        self.create_subscription(MissionState, "/redline/mission/state", self._on_mission, MISSION_QOS)
        self.counts = {"flights": 0, "records": 0, "rejected": 0}
        self._evidence = self.create_publisher(EvidenceRecord, EVIDENCE_TOPIC, EVIDENCE_QOS)
        group = ReentrantCallbackGroup()
        for action, name in ((ExecuteScout, SCOUT_ACTION), (SurveyArea, SURVEY_ACTION)):
            ActionServer(self, action, name, lambda handle, a=action: self._execute(handle, a),
                         goal_callback=lambda goal, a=action: self._accept(goal, a),
                         cancel_callback=lambda _: CancelResponse.ACCEPT, callback_group=group)
        self.get_logger().warning(f"SIMULATED {self.vehicle_id} stub over SCENARIO truth {self.truth_name}")

    # --- contract ---------------------------------------------------------------------
    def _area(self, goal, action):
        polygon = goal.corridor if action is ExecuteScout else goal.area
        return [(p.x, p.y) for p in polygon.points]

    def _on_mission(self, message):
        with self._lock:
            self._mission_phase = message.phase
            self._mission_receipt = time.monotonic()

    def _flight_allowed(self):
        with self._lock:
            fresh_precursor = self._mission_phase == MissionState.PRECURSOR and \
                0 <= time.monotonic()-self._mission_receipt <= self.mission_max_age_s
        return fresh_precursor and self.count_publishers(f"/{self.vehicle_id}/odom") == 0

    def _accept(self, goal, action) -> GoalResponse:
        area = self._area(goal, action)
        if not self._flight_allowed():
            self.counts["rejected"] += 1
            self.get_logger().warning("scout rejected: fresh PRECURSOR and no physical scout authority required")
            return GoalResponse.REJECT
        with self._lock:
            reason = None
            if self._busy:
                reason = "another survey is active"
            elif goal.vehicle_id != self.vehicle_id:
                reason = f"vehicle {goal.vehicle_id!r} is not {self.vehicle_id!r}"
            elif not goal.request_id or goal.request_id in self.seen_requests:
                reason = f"request id {goal.request_id!r} is empty or repeated"
            elif len(area) < 3 or not all(math.isfinite(v) for point in area for v in point) or abs(_signed_area(area)) < 1.0:
                reason = "the survey area needs a polygon of at least three points"
            elif action is ExecuteScout and (not math.isfinite(goal.altitude_m) or goal.altitude_m <= 0 or
                                             not math.isfinite(goal.max_flight_s) or goal.max_flight_s < 0):
                reason = "altitude must be positive and flight time limit nonnegative and finite"
            if reason:
                self.counts["rejected"] += 1
                self.get_logger().warning(f"{action.__name__} rejected: {reason}")
                return GoalResponse.REJECT
            self.seen_requests.add(goal.request_id)
            self._busy = True
        return GoalResponse.ACCEPT

    def _execute(self, handle, action):
        try:
            return self._execute_survey(handle, action)
        except Exception as error:
            self.get_logger().error(f"SIMULATED survey failed: {type(error).__name__}: {error}")
            if handle.is_active:
                handle.abort()
            return self._result(action, action.Result.FAILED, "survey execution failed", [], 0.0, 0)
        finally:
            with self._lock:
                self._busy = False

    def _execute_survey(self, handle, action):
        goal = handle.request
        area = self._area(goal, action)
        records = survey_evidence(self.world, self.grid, area, spacing_m=self.spacing_m,
                                  detection_limit_m=self.detection_limit_m, d_block_m=self.d_block_m)
        cx = sum(p[0] for p in area) / len(area)
        cy = sum(p[1] for p in area) / len(area)
        transit_s = math.hypot(cx - self.home_xy[0], cy - self.home_xy[1]) / self.speed_m_s
        survey_s = len(records) * self.spacing_m / self.speed_m_s
        plan = {"PREFLIGHT": 5.0, "TAKEOFF": self.phase_s, "TRANSIT": transit_s, "SURVEY": survey_s,
                "RETURN": transit_s, "LANDING": self.phase_s}
        if action is ExecuteScout and goal.max_flight_s > 0 and sum(plan.values()) > goal.max_flight_s:
            plan["SURVEY"] = max(0.0, goal.max_flight_s - (sum(plan.values()) - survey_s))
        published, flight_s = [], 0.0
        keep = int(round(len(records) * (plan["SURVEY"] / survey_s))) if survey_s > 0 else len(records)
        for phase in PHASES:
            duration = plan[phase]
            steps = max(1, int(math.ceil(duration / 10.0)))
            for k in range(steps):
                if handle.is_cancel_requested:
                    handle.canceled()
                    return self._result(action, action.Result.CANCELED, "cancelled in flight", published,
                                        flight_s, len(records))
                if not self._flight_allowed():
                    handle.abort()
                    return self._result(action, action.Result.FAILED, "PRECURSOR stale/ended or physical scout authority appeared",
                                        published, flight_s, len(records))
                time.sleep(duration / steps / self.time_scale)
                flight_s += duration / steps
                if phase == "SURVEY":
                    if not self._flight_allowed():
                        handle.abort()
                        return self._result(action, action.Result.FAILED, "PRECURSOR changed before evidence publication",
                                            published, flight_s, len(records))
                    upto = int(round(keep * (k + 1) / steps))
                    for x, y, radius, passable in records[len(published):upto]:
                        published.append(self._publish(goal.request_id, len(published), x, y, radius, passable))
                handle.publish_feedback(self._feedback(action, phase, flight_s, published, len(records)))
        handle.succeed()
        outcome = action.Result.SUCCEEDED if len(published) == len(records) else action.Result.PARTIAL
        self.counts["flights"] += 1
        return self._result(action, outcome, "" if outcome == action.Result.SUCCEEDED else "flight time limit",
                            published, flight_s, len(records))

    def _publish(self, request_id, index, x, y, radius, passable) -> str:
        record = EvidenceRecord()
        stamp = self.get_clock().now().to_msg()
        record.header.stamp, record.header.frame_id = stamp, "map"
        record.evidence_id = f"{request_id}-{index:04d}"
        record.measured = record.received = stamp
        record.source = "scout_stub"
        record.provenance.status = Provenance.SIMULATED
        record.provenance.product_id = self.truth_name
        record.provenance.note = "SIMULATED scout observation of SCENARIO truth (no Gazebo scout yet)"
        record.pose.pose.position.x, record.pose.pose.position.y = float(x), float(y)
        record.pose.pose.orientation.w = 1.0
        record.resolution_m = float(self.grid.resolution_m)
        record.quality = 1.0
        observation = {"schema": "redline.cell_observation.v2", "state": "DETECTED", "radius_m": float(radius)}
        if not passable:
            observation["passable"] = False
        record.summary_json = json.dumps({"cell_observation": observation})
        self._evidence.publish(record)
        self.counts["records"] += 1
        return record.evidence_id

    def _feedback(self, action, phase, flight_s, published, total):
        feedback = action.Feedback()
        feedback.phase = phase
        if action is ExecuteScout:
            feedback.battery_wh = float(-self.power_w * flight_s / 3600.0)
        else:
            feedback.covered_fraction = len(published) / total if total else 1.0
            feedback.new_evidence_ids = list(published[-20:])
        return feedback

    def _result(self, action, outcome, reason, published, flight_s, total):
        result = action.Result()
        result.outcome, result.reason, result.evidence_ids = outcome, reason, list(published)
        if action is ExecuteScout:
            result.flight_s = float(flight_s)
            result.battery_used_wh = float(self.power_w * flight_s / 3600.0)
        else:
            result.covered_fraction = len(published) / total if total else 1.0
            result.cost_s = float(flight_s)
            result.energy_wh = float(self.power_w * flight_s / 3600.0)
        return result


def _signed_area(points) -> float:
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ScoutStubNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
