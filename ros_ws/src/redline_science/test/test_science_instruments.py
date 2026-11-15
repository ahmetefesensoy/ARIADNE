"""Real DDS/action checks for science rehearsal and custody gates, not physics."""
import json
import math
from pathlib import Path
import time

import pytest
import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Point, Point32, Polygon, PoseStamped
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.lifecycle import TransitionCallbackReturn
from rclpy.parameter import Parameter
import yaml

from redline_msgs.action import CacheSample, CollectSample, ContactScience, DeployStation, Drill, NeutronSurvey, RemoteLibs
from redline_msgs.msg import EvidenceRecord, InstrumentProduct, Provenance, SampleRecord, ScalarField
from redline_science.science_instruments import ACTION_ENDPOINTS, EVENT_QOS, STATE_QOS, ScienceInstruments


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


class Rig:
    def __init__(self, tmp_path, *, active=True, simulated=True, power=500.0, duration=0.5):
        self.path = tmp_path
        self.location = [0.0, 0.0, 0.0]
        self.pose_enabled = True
        doc = {"seed": 7, "provenance_status": "SCENARIO", "noise_calibration": "UNCALIBRATED_SCENARIO",
            "targets": [{"id": "T1", "point_m": [0.0, 0.0, 0.0], "composition_percent": {"SiO2": 40.0, "FeO": 20.0},
                         "sigma_percent": 1.0, "weh_percent": 3.2, "hardness": 0.85, "input_ids": ["scenario-test-7"]}]}
        target_file = tmp_path / "targets.yaml"
        target_file.write_text(yaml.safe_dump(doc))
        self.node = ScienceInstruments(parameter_overrides=[
            Parameter("targets_file", value=str(target_file)), Parameter("products_dir", value=str(tmp_path / "products")),
            Parameter("run_id", value="science-test"), Parameter("simulated_backend", value=simulated),
            Parameter("available_power_w", value=power), Parameter("operation_duration_s", value=duration),
            Parameter("pose_max_age_s", value=0.5)])
        assert self.node.trigger_configure() == TransitionCallbackReturn.SUCCESS
        if active:
            assert self.node.trigger_activate() == TransitionCallbackReturn.SUCCESS
        self.probe = rclpy.create_node("science_probe")
        self.crew_pub = self.probe.create_publisher(PoseStamped, "/crew/EV1/pose", 10)
        self.robot_pub = self.probe.create_publisher(PoseStamped, "/redline/science/rover_pose", 10)
        self.probe.create_timer(0.025, self._pose)
        self.products, self.evidence, self.samples, self.fields = [], [], [], []
        self.probe.create_subscription(InstrumentProduct, "/redline/science/products", self.products.append, STATE_QOS)
        self.probe.create_subscription(EvidenceRecord, "/redline/evidence", self.evidence.append, EVENT_QOS)
        self.probe.create_subscription(SampleRecord, "/redline/science/samples", self.samples.append, STATE_QOS)
        self.probe.create_subscription(ScalarField, "/redline/science/fields", self.fields.append, STATE_QOS)
        self.clients = {kind: ActionClient(self.probe, kind, endpoint) for kind, endpoint in ACTION_ENDPOINTS.items()}
        self.executor = MultiThreadedExecutor(num_threads=4)
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)
        assert self.until(lambda: all(client.server_is_ready() for client in self.clients.values()))
        assert self.until(lambda: "EV1" in self.node._poses and "rover_1" in self.node._poses)

    def _pose(self):
        if not self.pose_enabled:
            return
        msg = PoseStamped()
        msg.header.stamp, msg.header.frame_id = self.probe.get_clock().now().to_msg(), "map"
        msg.pose.position = Point(x=self.location[0], y=self.location[1], z=self.location[2])
        msg.pose.orientation.w = 1.0
        self.crew_pub.publish(msg)
        self.robot_pub.publish(msg)

    def until(self, predicate, timeout=10.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.005)
            if predicate():
                return True
        return False

    def send(self, kind, goal, feedback=None):
        future = self.clients[kind].send_goal_async(goal, feedback_callback=feedback)
        assert self.until(future.done)
        return future.result()

    def finish(self, handle):
        future = handle.get_result_async()
        assert self.until(future.done)
        return future.result()

    def close(self):
        self.node._active = False
        self.executor.shutdown()
        for client in self.clients.values():
            client.destroy()
        self.node.destroy_node()
        self.probe.destroy_node()


def collect(request="collect-1", container="tube-1"):
    goal = CollectSample.Goal()
    goal.request_id, goal.crew_id, goal.target_id, goal.container_id = request, "EV1", "T1", container
    return goal


def test_collect_then_lab_record_preserves_origin_and_container(ros, tmp_path):
    rig = Rig(tmp_path)
    phases = []
    try:
        handle = rig.send(CollectSample, collect(), lambda f: phases.append(f.feedback.phase))
        assert handle.accepted
        completed = rig.finish(handle)
        assert completed.status == GoalStatus.STATUS_SUCCEEDED and completed.result.outcome == 0
        sample_id = completed.result.sample_id
        assert rig.node.samples[sample_id].state == SampleRecord.STOWED
        assert "ACQUIRING" in phases and "ACQUIRED" in phases
        rig.location = [20.0, 10.0, 0.0]
        assert rig.until(lambda: rig.node._poses["EV1"][0][0] == 20)
        cache = CacheSample.Goal()
        cache.request_id, cache.sample_id, cache.container_id = "cache-1", sample_id, "tube-1"
        cached = rig.send(CacheSample, cache)
        assert cached.accepted and rig.finish(cached).result.outcome == 0
        assert rig.until(lambda: any(s.state == SampleRecord.RECORDED for s in rig.samples))
        record = rig.node.samples[sample_id]
        assert record.origin_point == (0, 0, 0) and record.analysis_point == (20, 10, 0)
        assert record.container_id == "tube-1" and record.state == SampleRecord.RECORDED
        assert len(record.evidence_ids) == 2
        assert not rig.send(CacheSample, cache).accepted
        assert rig.until(lambda: len(rig.products) == 2 and len(rig.evidence) == 2)
        assert all(p.provenance.status == Provenance.SIMULATED for p in rig.products)
        assert all(Path(p.payload_uri).is_file() and Path(p.payload_uri).with_suffix(".xml").is_file() for p in rig.products)
        assert json.loads(rig.products[-1].summary_json)["request_id"] == "cache-1"
    finally:
        rig.close()


def test_repeat_and_occupied_container_are_rejected(ros, tmp_path):
    rig = Rig(tmp_path)
    try:
        handle = rig.send(CollectSample, collect())
        assert handle.accepted and rig.finish(handle).result.outcome == 0
        assert not rig.send(CollectSample, collect()).accepted
        assert not rig.send(CollectSample, collect("new-request", "tube-1")).accepted
    finally:
        rig.close()


def test_cancellation_emits_failed_sample_and_no_product(ros, tmp_path):
    rig = Rig(tmp_path, duration=1.5)
    try:
        handle = rig.send(CollectSample, collect())
        assert handle.accepted
        cancel = handle.cancel_goal_async()
        assert rig.until(cancel.done)
        result = rig.finish(handle)
        assert result.status == GoalStatus.STATUS_CANCELED and result.result.outcome == 2
        assert not list((tmp_path / "products/science-test").glob("sim-*.json"))
        assert all(sample.state == SampleRecord.FAILED for sample in rig.node.samples.values())
    finally:
        rig.close()


def test_stale_pose_aborts_operation_without_success_product(ros, tmp_path):
    rig = Rig(tmp_path, duration=1.5)
    try:
        handle = rig.send(CollectSample, collect())
        assert handle.accepted
        rig.pose_enabled = False
        result = rig.finish(handle)
        assert result.status == GoalStatus.STATUS_ABORTED and "stale" in result.result.reason
        assert not list((tmp_path / "products/science-test").glob("sim-*.json"))
    finally:
        rig.close()


@pytest.mark.parametrize("options", [{"active": False}, {"power": 0.0}])
def test_lifecycle_and_power_gates_reject(ros, tmp_path, options):
    rig = Rig(tmp_path, **options)
    try:
        assert not rig.send(CollectSample, collect()).accepted
    finally:
        rig.close()


def test_libs_contact_dan_drill_and_deploy_emit_lineage_and_fields(ros, tmp_path):
    # Observe every FDIR phase through DDS even when a parallel UE build
    # preempts this process; keep the phase assertions unchanged.
    rig = Rig(tmp_path,duration=2.0)
    try:
        libs = RemoteLibs.Goal()
        libs.request_id, libs.target_id = "libs-1", ""  # bounded autonomous nearest target
        libs.raster_rows = libs.raster_cols = 2
        libs.raster_spacing_mrad, libs.shots_per_point = 1.0, 5
        contact = ContactScience.Goal()
        contact.request_id, contact.target_id, contact.instrument, contact.integration_s = "xrf-1", "T1", "EV1_XRF", 20.0
        dan = NeutronSurvey.Goal()
        dan.request_id, dan.vehicle_id, dan.max_points, dan.dwell_s = "dan-1", "rover_1", 1, 20.0
        dan.area = Polygon(points=[Point32(x=-1.0, y=-1.0), Point32(x=1.0, y=-1.0), Point32(x=0.0, y=1.0)])
        drill = Drill.Goal()
        drill.request_id, drill.target_id, drill.depth_mm = "drill-1", "T1", 30.0
        deploy = DeployStation.Goal()
        deploy.request_id, deploy.deployer_id = "deploy-1", "EV1"
        drill_phases = []
        drill_status=[]
        from std_msgs.msg import String
        rig.probe.create_subscription(String,'/redline/science/status',lambda m:drill_status.append(json.loads(m.data)),STATE_QOS)
        for kind, goal in ((RemoteLibs, libs), (ContactScience, contact), (NeutronSurvey, dan), (Drill, drill), (DeployStation, deploy)):
            handle = rig.send(kind, goal, lambda f: drill_phases.append(getattr(f.feedback, "phase", "")))
            assert handle.accepted
            result = rig.finish(handle)
            assert result.status == GoalStatus.STATUS_SUCCEEDED and result.result.outcome == 0
        assert "STALL" in drill_phases and "PERCUSSIVE_RECOVERY" in drill_phases
        observed=[s for s in drill_status if s.get('request_id')=='drill-1' and 'depth_mm' in s]
        assert observed and all(0<=s['depth_mm']<=30 and s['physical_backend'] is False and s['status']=='SIMULATED' for s in observed)
        assert all(s['depth_source'].startswith('SIMULATED') for s in observed)
        assert rig.until(lambda: len(rig.products) == len(rig.evidence) == 5 and len(rig.fields) == 1)
        assert all(p.provenance.status == Provenance.SIMULATED for p in rig.products)
        assert {p.instrument for p in rig.products} == {"LIBS", "APXS", "DAN", "DRILL", "WEATHER"}
        field = rig.fields[0]
        assert field.width == field.height == 9 and len(field.data) == len(field.sigma) == 81
        assert all(math.isfinite(v) for v in field.data)
        products = [json.loads(p.summary_json) for p in rig.products]
        assert all("request_id" in p and p["noise_calibration"] == "UNCALIBRATED_SCENARIO" for p in products)
        assert next(p for p in products if "drill" in p)["drill"]["scenario_stall_recovered"]
    finally:
        rig.close()


def test_rejects_out_of_range_and_unknown_target_without_writing(ros, tmp_path):
    rig = Rig(tmp_path)
    try:
        invalid = collect()
        invalid.target_id = "unknown"
        assert not rig.send(CollectSample, invalid).accepted
        rig.location = [100.0, 0.0, 0.0]
        assert rig.until(lambda: rig.node._poses["EV1"][0][0] == 100)
        assert not rig.send(CollectSample, collect()).accepted
        assert not list((tmp_path / "products/science-test").glob("sim-*.json"))
    finally:
        rig.close()
