"""SIMULATED instruments behind the frozen science actions (proje.md sections 5/9).

The lifecycle and freshness/range gates are real. The sensor/contact/drill
measurements are authored SCENARIO rehearsals and never assert physical success.
No velocity, joint, TF or robot-odometry authority is published by this node.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import threading
import time

import rclpy
from geometry_msgs.msg import Point, PoseStamped
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float32, String

from redline_core.science_operations import (LIMITATION, ProductStore, Sample, SampleState, checked_id,
    finite_point, load_targets, phase_at, phases_for, polygon_contains, posterior_grid, readiness_error, synthetic_measurement)
from redline_msgs.action import CacheSample, CollectSample, ContactScience, DeployStation, Drill, NeutronSurvey, RemoteLibs
from redline_msgs.msg import EvidenceRecord, InstrumentProduct, Provenance, SampleRecord, ScalarField


STATE_QOS = QoSProfile(depth=16, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)
EVENT_QOS = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)
ACTION_ENDPOINTS = {RemoteLibs: "/rover_1/remote_libs", ContactScience: "/rover_1/contact_science",
    NeutronSurvey: "/rover_1/neutron_survey", Drill: "/rover_1/drill",
    CacheSample: "/redline/science/cache_sample", DeployStation: "/redline/science/deploy_station",
    CollectSample: "/redline/science/collect_sample"}
INSTRUMENTS = {RemoteLibs: "LIBS", ContactScience: "APXS", NeutronSurvey: "DAN", Drill: "DRILL",
               CacheSample: "SAMPLE", CollectSample: "SAMPLE", DeployStation: "WEATHER"}
POWER_W = {"LIBS": 30.0, "APXS": 8.0, "DAN": 25.0, "DRILL": 150.0, "SAMPLE": 2.0, "WEATHER": 5.0, "DOSIMETER": 5.0}


def xyz(point):
    return point.x, point.y, point.z


def point(values):
    return Point(x=float(values[0]), y=float(values[1]), z=float(values[2]))


class InstrumentBase(LifecycleNode):
    """Common lifecycle/readiness/product owner for scenario instrument adapters."""
    def __init__(self, **kwargs):
        super().__init__("science_instruments", **kwargs)
        get = lambda name, default: self.declare_parameter(name, default).value
        self.targets_file = str(get("targets_file", ""))
        self.products_dir = str(get("products_dir", ""))
        self.run_id = str(get("run_id", "science-preview"))
        self.simulated_enabled = bool(get("simulated_backend", False))
        self.physical_mode = bool(get("physical_mode", False))
        self.auto_activate = bool(get("auto_activate", False))
        self.duration_s = float(get("operation_duration_s", 8.0))
        self.available_power_w = float(get("available_power_w", 500.0))
        self.max_pose_age_s = float(get("pose_max_age_s", 2.0))
        self.robot_pose_topic = str(get("robot_pose_topic", "/redline/science/rover_pose"))
        self._active, self._configured = False, False
        self._busy = False
        self._lock = threading.RLock()
        self._poses = {}
        self.samples = {}
        self.containers = {}
        self._servers = []
        self._status_data = {"schema": "redline.science.status.v1", "phase": "UNCONFIGURED", "progress": 0.0,
                             "status": "SIMULATED", "physical_backend": False, "limitation": LIMITATION}
        self._status = self.create_publisher(String, "/redline/science/status", STATE_QOS)
        self._products = self.create_publisher(InstrumentProduct, "/redline/science/products", STATE_QOS)
        self._evidence = self.create_publisher(EvidenceRecord, "/redline/evidence", EVENT_QOS)
        self._samples = self.create_publisher(SampleRecord, "/redline/science/samples", STATE_QOS)
        self._fields = self.create_publisher(ScalarField, "/redline/science/fields", STATE_QOS)
        self._power = {key: self.create_publisher(Float32, f"/power/{key.lower()}", 10) for key in POWER_W}
        self._group = ReentrantCallbackGroup()
        for actor, topic in (("EV1", "/crew/EV1/pose"), ("EV2", "/crew/EV2/pose"), ("rover_1", self.robot_pose_topic)):
            self.create_subscription(PoseStamped, topic, lambda msg, who=actor: self._pose(msg, who), 10,
                                     callback_group=self._group)
        for action, name in ACTION_ENDPOINTS.items():
            self._servers.append(ActionServer(self, action, name,
                lambda handle, kind=action: self._execute(handle, kind),
                goal_callback=lambda goal, kind=action: self._accept(goal, kind),
                cancel_callback=lambda _: CancelResponse.ACCEPT, callback_group=self._group))
        self._status_timer = self.create_timer(0.25, self._publish_status)
        if self.auto_activate:
            self._startup_timer = self.create_timer(0.1, self._startup)

    def _startup(self):
        self._startup_timer.cancel()
        if self.trigger_configure() == TransitionCallbackReturn.SUCCESS:
            self.trigger_activate()

    def on_configure(self, state):
        try:
            if not self.targets_file or not self.products_dir:
                raise ValueError("targets_file and products_dir are required")
            if not math.isfinite(self.duration_s) or not 0.1 <= self.duration_s <= 120:
                raise ValueError("operation_duration_s must be in [0.1,120]")
            if not math.isfinite(self.max_pose_age_s) or not 0 < self.max_pose_age_s <= 5:
                raise ValueError("pose_max_age_s must be in (0,5]")
            self.seed, self.targets, self.registry = load_targets(self.targets_file)
            self.store = ProductStore(self.products_dir, self.run_id)
            self._load_samples()
        except (OSError, ValueError, KeyError) as error:
            self.get_logger().error(str(error))
            return TransitionCallbackReturn.FAILURE
        self._configured = True
        self._status_data["phase"] = "STANDBY"
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state):
        if not self._configured or not self.simulated_enabled or self.physical_mode:
            self.get_logger().error("activation needs explicit SIMULATED opt-in; no physical backend exists")
            return TransitionCallbackReturn.FAILURE
        self._active = True
        self._status_data["phase"] = "READY"
        self.get_logger().warning(LIMITATION)
        return super().on_activate(state)

    def on_deactivate(self, state):
        self._active = False
        return super().on_deactivate(state)

    def on_cleanup(self, state):
        self._active, self._configured = False, False
        self._status_data["phase"] = "UNCONFIGURED"
        return TransitionCallbackReturn.SUCCESS

    def _load_samples(self):
        for source in self.store.path.glob("sample-*.json"):
            doc = json.loads(source.read_text(encoding="utf-8"))
            sample = Sample(doc["sample_id"], doc["target_id"], finite_point(doc["origin_point_m"]),
                finite_point(doc["analysis_point_m"]), doc["tool"], doc["container_id"], SampleState(doc["state"]),
                list(doc["evidence_ids"]))
            self.samples[sample.sample_id] = sample
            if sample.container_id:
                self.containers[sample.container_id] = sample.sample_id

    def _pose(self, msg, actor):
        if msg.header.frame_id != "map":
            return
        try:
            location = finite_point(xyz(msg.pose.position))
        except ValueError:
            return
        with self._lock:
            self._poses[actor] = (location, time.monotonic())

    def _actor(self, goal, kind):
        if kind is CollectSample:
            return goal.crew_id
        if kind is ContactScience and goal.instrument == "EV1_XRF":
            return "EV1"
        if kind is DeployStation:
            return goal.deployer_id
        if kind is CacheSample:
            return "EV1"
        return "rover_1"

    def _target(self, goal, kind):
        if kind is CacheSample:
            sample = self.samples.get(goal.sample_id)
            return self.targets.get(sample.target_id) if sample else None
        if kind in (NeutronSurvey, DeployStation):
            position = xyz(goal.position) if kind is DeployStation else (
                (goal.area.points[0].x, goal.area.points[0].y, 0.0) if goal.area.points else (math.nan,) * 3)
            candidates = list(self.targets.values())
            if kind is NeutronSurvey:
                polygon = [(p.x, p.y) for p in goal.area.points]
                candidates = [target for target in candidates if polygon_contains(target.point[:2], polygon)]
            return min(candidates, key=lambda t: math.hypot(t.point[0] - position[0], t.point[1] - position[1])) if candidates else None
        if kind is RemoteLibs and not goal.target_id:
            pose = self._poses.get("rover_1")
            return min(self.targets.values(), key=lambda t: math.dist(t.point, pose[0])) if pose else None
        return self.targets.get(goal.target_id)

    def _validate(self, goal, kind):
        if not self._configured:
            return "instrument not configured"
        actor = self._actor(goal, kind)
        if actor not in ("EV1", "EV2", "rover_1"):
            return "unknown actor"
        target = self._target(goal, kind)
        if target is None:
            return "unknown target or sample"
        snapshot = self._poses.get(actor)
        pose, age = (snapshot[0], time.monotonic() - snapshot[1]) if snapshot else (None, math.inf)
        instrument = INSTRUMENTS[kind]
        destination = target.point
        max_range = 7.0 if kind is RemoteLibs else 4.0
        if kind is CacheSample:
            destination, max_range = pose or target.point, 4.0
            sample = self.samples.get(goal.sample_id)
            if sample is None or sample.state not in (SampleState.ACQUIRED, SampleState.STOWED):
                return "sample must be ACQUIRED or STOWED before caching"
            checked_id(goal.container_id)
            if goal.container_id in self.containers and self.containers[goal.container_id] != sample.sample_id:
                return "container already occupied"
        if kind in (ContactScience, CollectSample):
            if math.dist(finite_point(xyz(goal.target_point)), target.point) > 0.5:
                return "requested point differs from registered target"
        if kind is CollectSample:
            checked_id(goal.container_id)
            if goal.container_id in self.containers:
                return "container already occupied"
        if kind is ContactScience:
            if goal.instrument not in ("APXS", "EV1_XRF") or not 0 < goal.integration_s <= 3600:
                return "unsupported contact instrument or integration duration"
        if kind is RemoteLibs:
            if not (1 <= goal.raster_rows <= 8 and 1 <= goal.raster_cols <= 8 and 1 <= goal.shots_per_point <= 100):
                return "raster/shot count outside bounded rehearsal limits"
            if not math.isfinite(goal.raster_spacing_mrad) or not 0 < goal.raster_spacing_mrad <= 100:
                return "invalid raster spacing"
        if kind is Drill and (not math.isfinite(goal.depth_mm) or not 0 < goal.depth_mm <= 100 or goal.mode not in (0, 1)):
            return "drill depth/mode outside scenario limits"
        if kind is NeutronSurvey:
            if goal.vehicle_id != "rover_1" or goal.max_points != 1 or not 0 < goal.dwell_s <= 3600 or goal.mode not in (0, 1):
                return "invalid neutron survey limits or vehicle"
            if len(goal.area.points) < 3:
                return "survey area needs a polygon"
        if kind is DeployStation:
            if goal.station_type not in (0, 1) or math.dist(finite_point(xyz(goal.position)), target.point) > 4:
                return "station position/type invalid"
        return readiness_error(active=self._active, simulated_enabled=self.simulated_enabled,
            physical_mode=self.physical_mode, pose=pose, age_s=age, target=destination, max_range_m=max_range,
            available_power_w=self.available_power_w, required_power_w=POWER_W[instrument], max_age_s=self.max_pose_age_s)

    def _accept(self, goal, kind):
        with self._lock:
            try:
                checked_id(goal.request_id)
                reason = "instrument operation already active" if self._busy else self._validate(goal, kind)
                if not reason and not self.store.reserve_request(goal.request_id):
                    reason = "request id already accepted in this run (persistent repeat protection)"
            except (ValueError, KeyError, TypeError) as error:
                reason = str(error)
            if reason:
                self.get_logger().warning(f"{kind.__name__} rejected: {reason}")
                return GoalResponse.REJECT
            self._busy = True
            return GoalResponse.ACCEPT

    def _publish_status(self):
        self._status.publish(String(data=json.dumps(self._status_data, allow_nan=False)))

    def _save_sample(self, sample):
        temporary = self.store.path / f"sample-{sample.sample_id}.tmp"
        temporary.write_text(json.dumps(sample.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.store.path / f"sample-{sample.sample_id}.json")
        msg = SampleRecord()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.sample_id, msg.target_id, msg.tool, msg.container_id = sample.sample_id, sample.target_id, sample.tool, sample.container_id
        msg.origin_point, msg.analysis_point = point(sample.origin_point), point(sample.analysis_point)
        msg.state, msg.evidence_ids = int(sample.state), list(sample.evidence_ids)
        self._samples.publish(msg)

    def _execute(self, handle, kind):
        goal, instrument = handle.request, INSTRUMENTS[kind]
        if kind is DeployStation and goal.station_type == DeployStation.Goal.DOSIMETER:
            instrument = "DOSIMETER"
        result = kind.Result()
        sample = None
        try:
            target = self._target(goal, kind)
            actor = self._actor(goal, kind)
            integration = float(goal.integration_s) if kind is ContactScience else (
                float(goal.dwell_s) if kind is NeutronSurvey else 20.0)
            if kind in (Drill, CollectSample):
                suffix = hashlib.sha256(goal.request_id.encode()).hexdigest()[:12]
                sample = Sample(f"smp-BXW-{suffix}", target.target_id, target.point, self._poses[actor][0],
                                "DRILL_SCENARIO" if kind is Drill else "CREW_SCOOP_SCENARIO",
                                goal.container_id if kind is CollectSample else "")
                self.samples[sample.sample_id] = sample
                self._save_sample(sample)
            elif kind is CacheSample:
                sample = self.samples[goal.sample_id]
                sample.analysis_point = self._poses[actor][0]
                sample.container_id = goal.container_id
                self.containers[goal.container_id] = sample.sample_id
            stall = kind is Drill and target.hardness > 0.7 and goal.mode == Drill.Goal.ROTARY
            phases = phases_for("DRILL" if kind is CollectSample else instrument, stall=stall)
            started = time.monotonic()
            self._power[instrument].publish(Float32(data=POWER_W[instrument]))
            last_phase = ""
            while True:
                if handle.is_cancel_requested:
                    if sample and sample.state < SampleState.ACQUIRED:
                        sample.advance(SampleState.FAILED)
                        self._save_sample(sample)
                    handle.canceled()
                    result.outcome, result.reason = result.CANCELED, "operation canceled; no successful product emitted"
                    return result
                error = self._validate_running(goal, kind)
                if error:
                    if sample and sample.state < SampleState.ACQUIRED:
                        sample.advance(SampleState.FAILED)
                        self._save_sample(sample)
                    handle.abort()
                    result.outcome, result.reason = result.FAILED, error
                    return result
                elapsed = time.monotonic() - started
                phase, progress = phase_at(phases, elapsed, self.duration_s)
                self._status_data = {"schema": "redline.science.status.v1", "request_id": goal.request_id,
                    "actor_id": actor, "instrument": instrument, "target_id": target.target_id,
                    "target_point_m": list(target.point), "phase": phase, "progress": progress,
                    "elapsed_wall_s": elapsed, "integration_s": integration, "status": "SIMULATED",
                    "physical_backend": False, "limitation": LIMITATION}
                if sample and phase != last_phase and phase in SampleState.__members__:
                    next_state = SampleState[phase]
                    # A busy executor can cross a wall-time phase boundary.
                    # Emit each intervening custody state in order rather than
                    # skipping the state machine because a feedback tick was late.
                    while next_state > sample.state and sample.state < SampleState.RECORDED:
                        sample.advance(SampleState(int(sample.state) + 1))
                        self._save_sample(sample)
                feedback = kind.Feedback()
                if hasattr(feedback, "phase"):
                    feedback.phase = phase
                if hasattr(feedback, "progress"):
                    feedback.progress = progress
                if hasattr(feedback, "elapsed_s"):
                    feedback.elapsed_s = elapsed
                if hasattr(feedback, "points_done"):
                    count = goal.max_points if kind is NeutronSurvey else goal.raster_rows * goal.raster_cols
                    feedback.points_done = int(progress * count)
                if kind is Drill:
                    feedback.depth_mm = goal.depth_mm * progress
                    feedback.feed_force_n = 10.0 if phase not in ("STALL", "RETRACT") else 0.0
                    feedback.torque_nm = 3.0 if phase == "STALL" else 0.4
                    self._status_data.update(depth_mm=feedback.depth_mm,
                        feed_force_n=feedback.feed_force_n,torque_nm=feedback.torque_nm,
                        depth_source="SIMULATED action feedback; not a physical depth sensor")
                if kind is NeutronSurvey:
                    feedback.max_posterior_sigma = target.sigma_percent / math.sqrt(max(1, feedback.points_done))
                if phase != last_phase or elapsed == 0 or progress == 1:
                    handle.publish_feedback(feedback)
                last_phase = phase
                if progress >= 1:
                    break
                time.sleep(min(0.05, self.duration_s / (4 * len(phases))))
            measurement = synthetic_measurement(target, instrument, goal.request_id, self.seed, integration)
            if kind is Drill:
                measurement["drill"] = {"requested_depth_mm": goal.depth_mm, "achieved_depth_mm": goal.depth_mm,
                    "scenario_stall_recovered": stall, "recovery": ["RETRACT", "REDUCE_FEED", "PERCUSSIVE"] if stall else [],
                    "physical_force_sensor": False}
            if kind is NeutronSurvey:
                measurement["posterior_grid"] = posterior_grid([target.point], measurement["values"], target.sigma_percent)
            if sample:
                sample.analysis_point = self._poses[actor][0]
                if sample.state != SampleState.RECORDED and kind in (CacheSample, CollectSample):
                    # Field collection seals the sample. Lab custody records it
                    # later, preserving its original collection point.
                    if kind is CollectSample:
                        self.containers[sample.container_id] = sample.sample_id
                    if sample.state == SampleState.ACQUIRED:
                        sample.advance(SampleState.STOWED)
                        self._save_sample(sample)
                    if kind is CacheSample and sample.state == SampleState.STOWED:
                        sample.advance(SampleState.RECORDED)
                self._save_sample(sample)
            payload = self.store.write(request_id=goal.request_id, instrument=instrument, target=target,
                measured_utc=datetime.now(timezone.utc).isoformat(), integration_s=integration,
                instrument_point=self._poses[actor][0], measurement=measurement, sample=sample)
            if sample:
                sample.evidence_ids.append(payload["evidence_id"])
                self._save_sample(sample)
            self._emit_product(payload, target, actor, integration)
            if kind is NeutronSurvey:
                self._emit_field(measurement["posterior_grid"], payload)
            if hasattr(result, "product_id"):
                result.product_id = payload["product_id"]
            if hasattr(result, "product_ids"):
                result.product_ids = [payload["product_id"]]
            if kind is RemoteLibs:
                result.chosen_target_id = target.target_id
            if kind is ContactScience:
                result.achieved_contact_angle_deg = math.nan  # no physical contact assertion
            if kind is NeutronSurvey:
                result.field_name = "weh_percent"
            if kind in (Drill, CollectSample):
                result.sample_id = sample.sample_id
            if kind is Drill:
                result.fault_code, result.achieved_depth_mm = "", goal.depth_mm
            if kind is DeployStation:
                result.station_id = "station-" + hashlib.sha256(goal.request_id.encode()).hexdigest()[:12]
            result.outcome, result.reason = result.SUCCEEDED, LIMITATION
            handle.succeed()
            self._status_data.update(phase="COMPLETE", progress=1.0, product_id=payload["product_id"],
                                     sample_id=sample.sample_id if sample else "")
            return result
        except Exception as error:
            self.get_logger().error(f"{kind.__name__}: {type(error).__name__}: {error}")
            if handle.is_active:
                handle.abort()
            result.outcome, result.reason = result.FAILED, str(error)[:256]
            self._status_data.update(phase="FAILED", reason=result.reason)
            return result
        finally:
            self._power[instrument].publish(Float32(data=0.0))
            with self._lock:
                self._busy = False

    def _validate_running(self, goal, kind):
        # Custody state advances during execution; its acceptance-only checks do
        # not apply a second time. Keep lifecycle, pose, power and range live.
        if not self._active:
            return "instrument deactivated during operation"
        actor = self._actor(goal, kind)
        snapshot = self._poses.get(actor)
        target = self._target(goal, kind)
        if snapshot is None or target is None:
            return "pose or target unavailable during operation"
        destination = snapshot[0] if kind is CacheSample else target.point
        return readiness_error(active=True, simulated_enabled=self.simulated_enabled, physical_mode=self.physical_mode,
            pose=snapshot[0], age_s=time.monotonic() - snapshot[1], target=destination,
            max_range_m=7.0 if kind is RemoteLibs else 4.0, available_power_w=self.available_power_w,
            required_power_w=POWER_W[INSTRUMENTS[kind]], max_age_s=self.max_pose_age_s)

    def _emit_product(self, payload, target, actor, integration):
        msg = InstrumentProduct()
        msg.header.stamp, msg.header.frame_id = self.get_clock().now().to_msg(), "map"
        msg.product_id, msg.instrument, msg.target_id = payload["product_id"], payload["instrument"], target.target_id
        msg.target_point, msg.instrument_pose.pose.position = point(target.point), point(self._poses[actor][0])
        msg.instrument_pose.pose.orientation.w = 1.0
        msg.integration_s = integration
        msg.payload_uri = payload["payload_uri"]
        msg.summary_json = json.dumps({"schema": "redline.science.summary.v1", "request_id": payload["request_id"],
                                      **payload["measurement"],
                                      "sample": payload.get("sample"), "status": "SIMULATED"}, allow_nan=False)
        msg.provenance.status, msg.provenance.product_id = Provenance.SIMULATED, msg.product_id
        msg.provenance.sha256, msg.provenance.note = payload["sha256"], LIMITATION
        msg.provenance.version, msg.provenance.source_url = "science-rehearsal-v1", self.targets_file
        msg.provenance.acquired = msg.header.stamp
        self._products.publish(msg)
        evidence = EvidenceRecord()
        evidence.header, evidence.measured, evidence.received = msg.header, msg.header.stamp, msg.header.stamp
        evidence.evidence_id, evidence.source = payload["evidence_id"], "science_instruments_simulated"
        evidence.provenance, evidence.pose = msg.provenance, msg.instrument_pose
        evidence.quality, evidence.resolution_m = 0.0, 0.0  # uncalibrated, no science-quality claim
        evidence.input_ids, evidence.payload_uri = list(payload["input_ids"]), msg.payload_uri
        evidence.summary_json = msg.summary_json
        self._evidence.publish(evidence)

    def _emit_field(self, grid, payload):
        field = ScalarField()
        field.header.stamp, field.header.frame_id = self.get_clock().now().to_msg(), "map"
        field.site_id, field.name, field.unit = "BXW", "weh_percent", grid["unit"]
        field.origin = point([*grid["origin_m"], 0.0])
        field.resolution_m, field.width, field.height = grid["resolution_m"], grid["width"], grid["height"]
        field.data, field.sigma = grid["values"], grid["sigma"]
        field.provenance.status, field.provenance.product_id = Provenance.SIMULATED, payload["product_id"]
        field.provenance.note = LIMITATION
        self._fields.publish(field)


ScienceInstruments = InstrumentBase


def main(args=None):
    rclpy.init(args=args)
    node = ScienceInstruments()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node._active = False
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()
