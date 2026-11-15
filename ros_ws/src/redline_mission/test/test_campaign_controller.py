"""Campaign service + real science actions, with explicit DDS scout/Nav2 fixtures.

The fixtures prove orchestration only. They do not prove drone flight, Nav2
collision avoidance or Gazebo contact/drilling; those have separate acceptance.
"""
from concurrent.futures import Future
import json
from pathlib import Path
import time
from types import SimpleNamespace

import pytest
import rclpy
from geometry_msgs.msg import Point, PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
import yaml

from redline_mission.campaign_controller import CampaignController, MAP_QOS
from redline_msgs.action import ExecuteScout
from redline_msgs.msg import Alert, CrewState, EvidenceRecord, InstrumentProduct, MissionState, SampleRecord
from redline_msgs.srv import MissionCommand
from redline_science.science_instruments import ScienceInstruments


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


class Rig:
    def __init__(self, tmp_path, *, scout_evidence=True, duration=0.3):
        self.crew_location = [285.1, -456.0, 0.0]
        self.robot_location = [303.0, -454.0, 0.0]
        self.scout_evidence, self.scout_count, self.nav_count = scout_evidence, 0, 0
        self.publish_robot = True
        self.path = tmp_path
        targets = {"seed": 7, "provenance_status": "SCENARIO", "noise_calibration": "UNCALIBRATED_SCENARIO",
            "targets": [{"id": name, "point_m": location, "composition_percent": {"SiO2": 40.0, "FeO": 20.0},
                "sigma_percent": 1.0, "weh_percent": 3.2, "hardness": 0.85, "input_ids": ["campaign-dds-fixture-7"]}
                for name, location in (("BXW_RIDGE_A", [306.0, -454.0, 0.0]), ("BXW_HOLLOW_B", [320.0, -448.0, 0.0]))]}
        self.target_file = tmp_path / "targets.yaml"
        self.target_file.write_text(yaml.safe_dump(targets))
        self.controller = CampaignController(parameter_overrides=[
            Parameter("redline_root", value=str(tmp_path)), Parameter("targets_file", value=str(self.target_file)),
            Parameter("run_id", value="campaign-dds-test"), Parameter("campaign_output_dir", value=str(tmp_path / "products"))])
        self.science = ScienceInstruments(parameter_overrides=[
            Parameter("targets_file", value=str(self.target_file)), Parameter("products_dir", value=str(tmp_path / "products")),
            Parameter("run_id", value="campaign-dds-test"), Parameter("simulated_backend", value=True),
            Parameter("operation_duration_s", value=duration), Parameter("auto_activate", value=True)])
        self.probe = rclpy.create_node("sim_clock")
        self.probe.declare_parameter("running", False)
        self.crew_pub = self.probe.create_publisher(CrewState, "/crew/EV1/state", 10)
        self.pose_pub = self.probe.create_publisher(PoseStamped, "/crew/EV1/pose", 10)
        self.robot_pub = self.probe.create_publisher(PoseStamped, "/redline/science/rover_pose", 10)
        self.evidence_pub = self.probe.create_publisher(EvidenceRecord, "/redline/evidence", 50)
        self.alert_pub = self.probe.create_publisher(Alert, "/redline/alerts", 50)
        self.clock_pub = self.probe.create_publisher(Clock, "/redline/mission/clock", 10)
        self.physics_pub = self.probe.create_publisher(Clock, "/clock", 10)
        self.probe.create_timer(0.025, self._publish)
        self.commands = self.probe.create_client(MissionCommand, "/redline/campaign/command")
        group = ReentrantCallbackGroup()
        self.scout = ActionServer(self.probe, ExecuteScout, "/scout_1/execute_scout", self._scout,
                                  callback_group=group, cancel_callback=lambda _: CancelResponse.ACCEPT)
        self.nav = ActionServer(self.probe, NavigateToPose, "/rover_1/navigate_to_pose", self._nav,
                                callback_group=group, cancel_callback=lambda _: CancelResponse.ACCEPT)
        self.executor = MultiThreadedExecutor(num_threads=6)
        for node in (self.controller, self.science, self.probe):
            self.executor.add_node(node)
        assert self.until(lambda: self.commands.service_is_ready() and self.science._active
                          and self.controller.crew is not None and self.controller._action_clients["collect"].server_is_ready())

    def _publish(self):
        pose = PoseStamped()
        pose.header.frame_id, pose.header.stamp = "map", self.probe.get_clock().now().to_msg()
        pose.pose.position = Point(x=self.crew_location[0], y=self.crew_location[1], z=self.crew_location[2])
        pose.pose.orientation.w = 1.0
        self.pose_pub.publish(pose)
        crew = CrewState()
        crew.header, crew.crew_id = pose.header, "EV1"
        crew.pose.pose = pose.pose
        self.crew_pub.publish(crew)
        if self.publish_robot:
            robot = PoseStamped()
            robot.header = pose.header
            robot.pose.position = Point(x=self.robot_location[0], y=self.robot_location[1], z=self.robot_location[2])
            robot.pose.orientation.w = 1.0
            self.robot_pub.publish(robot)
        clock = Clock()
        clock.clock.sec = 10 if self.probe.get_parameter("running").value else 0
        self.clock_pub.publish(clock)
        physics = Clock()
        physics.clock.sec = 123
        self.physics_pub.publish(physics)

    def _scout(self, handle):
        self.scout_count += 1
        result = ExecuteScout.Result()
        if self.scout_evidence:
            evidence = EvidenceRecord()
            evidence.header.frame_id = "map"
            evidence.evidence_id, evidence.source = "ev-campaign-scout-fixture", "DDS_TEST_FIXTURE_NOT_FLIGHT"
            evidence.provenance.status = evidence.provenance.SIMULATED
            evidence.summary_json = '{"status":"SIMULATED","fixture":true}'
            self.evidence_pub.publish(evidence)
            result.evidence_ids = [evidence.evidence_id]
        result.outcome, result.reason = result.SUCCEEDED, "DDS fixture only; no physical flight"
        handle.succeed()
        return result

    def _nav(self, handle):
        self.nav_count += 1
        assert handle.request.pose.header.stamp.sec == 123  # physics stamp, never host UTC or PET
        target = handle.request.pose.pose.position
        self.robot_location = [target.x, target.y, target.z]
        result = NavigateToPose.Result()
        result.error_code = 0
        handle.succeed()
        return result

    def until(self, predicate, timeout=12.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.executor.spin_once(timeout_sec=0.005)
            if predicate():
                return True
        return False

    def move_to_task(self):
        target = self.controller.campaign.task.xy
        self.crew_location = [*target, 0.0]
        assert self.until(lambda: self.controller.crew.pose.pose.position.x == target[0]
                          and self.controller.crew.pose.pose.position.y == target[1])

    def command(self, command="START", *, request_id=None, revision=None, target=None):
        campaign = self.controller.campaign
        request = MissionCommand.Request(request_id=request_id or f"rq-{campaign.revision}-{command}",
            command=command, target_id=target or campaign.task.target_id,
            expected_revision=campaign.revision if revision is None else revision)
        future = self.commands.call_async(request)
        assert self.until(future.done)
        return future.result(), request

    def complete_current(self, command="START"):
        self.move_to_task()
        previous = self.controller.campaign.index
        response, _ = self.command(command)
        assert response.accepted, response.reason
        advanced = self.until(lambda: self.controller.campaign.index > previous)
        if not advanced:
            detail = {"task": self.controller.campaign.task.id, "message": self.controller.campaign.message,
                "operation": self.controller.campaign.operation_id,
                "products": [(pid, doc["summary"].get("request_id")) for pid, doc in self.controller.products.items()],
                "evidence": {pid: list(values) for pid, values in self.controller._evidence_by_product.items()},
                "samples": [(sid, doc["state"]) for sid, doc in self.controller.samples.items()]}
            raise AssertionError(json.dumps(detail))

    def close(self):
        self.science._active = False
        self.executor.shutdown()
        self.scout.destroy()
        self.nav.destroy()
        for node in (self.controller, self.science, self.probe):
            node.destroy_node()


def test_twelve_step_campaign_uses_science_results_custody_and_decisions(ros, tmp_path):
    rig = Rig(tmp_path)
    try:
        while not rig.controller.campaign.done:
            kind = rig.controller.campaign.task.kind
            command = {"decision": "CHOOSE_RIDGE", "assessment": "NEED_MORE_DATA"}.get(kind, "START")
            rig.complete_current(command)
        campaign = rig.controller.campaign
        assert len(campaign.completed) == 12 and rig.scout_count == rig.nav_count == 1
        assert rig.probe.get_parameter("running").value
        assert len(campaign.product_ids) == 7
        assert len(campaign.evidence_ids) == 8
        assert all(rig.controller._evidence_by_product[p] for p in campaign.product_ids)
        sample = rig.controller.samples[campaign.sample_ids[0]]
        assert sample["state"] == SampleRecord.RECORDED
        assert sample["origin_point_m"] == [306.0, -454.0, 0.0]
        assert sample["analysis_point_m"] == [285.1, -468.0, 0.0]
        assert sample["origin_point_m"] != sample["analysis_point_m"]
        assert campaign.decisions[-1]["chosen"] == "NEED_MORE_DATA"
        products = list((tmp_path / "products/campaign-dds-test").glob("sim-*.json"))
        assert len(products) == 7 and all(path.with_suffix(".xml").is_file() for path in products)
        assert all(json.loads(path.read_text())["provenance_status"] == "SIMULATED" for path in products)
    finally:
        rig.close()


def test_empty_scout_success_never_unlocks_route_decision(ros, tmp_path):
    rig = Rig(tmp_path, scout_evidence=False)
    try:
        rig.complete_current()
        response, _ = rig.command()
        assert response.accepted
        assert rig.until(lambda: rig.controller.campaign.state == "failed")
        assert rig.controller.campaign.task.id == "scout" and "scout" not in rig.controller.campaign.completed
    finally:
        rig.close()


def test_duplicate_service_call_never_dispatches_twice(ros, tmp_path):
    rig = Rig(tmp_path)
    try:
        rig.complete_current()
        response, request = rig.command(request_id="scout-once")
        assert response.accepted
        future = rig.commands.call_async(request)
        assert rig.until(future.done) and future.result().accepted
        assert rig.until(lambda: rig.controller.campaign.task.id == "route")
        assert rig.scout_count == 1
    finally:
        rig.close()


def test_sep_stops_science_and_does_not_credit_the_operation(ros, tmp_path):
    rig = Rig(tmp_path, duration=2.0)
    try:
        rig.complete_current()
        rig.complete_current()
        rig.complete_current("CHOOSE_RIDGE")
        rig.move_to_task()
        response, _ = rig.command()
        assert response.accepted
        assert rig.until(lambda: rig.controller._goal is not None)
        alert = Alert(code="SEP_ALERT", severity=Alert.EMERGENCY)
        rig.alert_pub.publish(alert)
        assert rig.until(lambda: rig.controller.sep_alert and rig.controller.campaign.state == "failed")
        assert rig.controller.campaign.task.id == "collect"
        assert "collect" not in rig.controller.campaign.completed
        assert not rig.command()[0].accepted
    finally:
        rig.close()


def test_late_old_goal_result_is_fenced_from_current_task(ros, tmp_path):
    rig = Rig(tmp_path)
    class LateHandle:
        accepted = True
        canceled = False
        def cancel_goal_async(self):
            self.canceled = True
    try:
        rig.controller.campaign.operation_id = "current-operation"
        rig.controller.campaign.state = "running"
        late = LateHandle()
        future = Future()
        future.set_result(late)
        rig.controller._goal_response(future, "collect", "old-operation")
        assert late.canceled and rig.controller._goal is None
        result = Future()
        result.set_result(SimpleNamespace(status=4, result=SimpleNamespace(outcome=0)))
        rig.controller._result(result, "collect", "old-operation")
        assert rig.controller.campaign.index == 0 and rig.controller.campaign.operation_id == "current-operation"
    finally:
        rig.close()


def test_malformed_status_products_and_wrong_frame_cannot_break_controller(ros, tmp_path):
    rig = Rig(tmp_path)
    try:
        for payload in ("[]", '{"value":NaN}', "not-json"):
            rig.controller._science_status(String(data=payload))
            product = InstrumentProduct(product_id="bad", summary_json=payload)
            rig.controller._product(product)
        assert "bad" not in rig.controller.products
        rig.controller._robot_receipt = -float("inf")
        pose = PoseStamped()
        pose.header.frame_id = "rover_1/odom"
        rig.controller._robot_pose(pose)
        assert rig.controller._robot_receipt == -float("inf")
    finally:
        rig.close()


def test_scout_observations_survive_late_join_and_remain_bounded(ros, tmp_path):
    rig = Rig(tmp_path)
    controller = rig.controller

    def record(index, *, summary=None):
        msg = EvidenceRecord(evidence_id=f"obs-{index:04d}", source="scout_flight_simulated_observer")
        msg.header.frame_id = "map"
        msg.pose.pose.position = Point(x=float(index), y=-5., z=-3500.)
        msg.provenance.status = msg.provenance.SIMULATED
        msg.provenance.product_id = "fixture-truth"
        msg.summary_json = json.dumps(summary if summary is not None else {
            "cell_observation": {"schema": "redline.cell_observation.v2", "state": "DETECTED"}})
        return msg

    try:
        first = record(0, summary={"passability": 0, "ignored_blob": "not retained"})
        controller._evidence_record(first)
        first.pose.pose.position.x = 999.
        controller._evidence_record(first)
        retained = controller._scout_observations[first.evidence_id]
        assert retained["pose"]["pose"]["position"]["x"] == 0.
        assert json.loads(retained["summary_json"]) == {"passability": 0}

        for index, mutate in enumerate((
                lambda m: setattr(m.header, "frame_id", "scout_1/odom"),
                lambda m: setattr(m.pose.pose.position, "x", float("nan")),
                lambda m: setattr(m.pose.pose.position, "z", 1e8),
                lambda m: setattr(m, "source", "EV1_XRF"),
                lambda m: setattr(m, "source", "scout" + "x" * 64),
                lambda m: setattr(m, "summary_json", '{"passability":NaN}'),
                lambda m: setattr(m, "summary_json", '[]'),
                lambda m: setattr(m, "summary_json", "x" * 8193),
                lambda m: setattr(m, "evidence_id", "x" * 257),
                lambda m: setattr(m.provenance, "status", 255)), 1000):
            invalid = record(index)
            mutate(invalid)
            controller._evidence_record(invalid)
        assert list(controller._scout_observations) == [first.evidence_id]

        for index in range(1, 131):
            msg = record(index)
            if index == 129:
                msg.summary_json = json.dumps({"cell_observation": {
                    "schema": "redline.cell_observation.v2", "state": "DETECTED", "passable": False}})
            controller._evidence_record(msg)
        assert len(controller._scout_observations) == 128
        assert next(iter(controller._scout_observations)) == "obs-0003"
        controller._evidence_record(first)  # An evicted duplicate cannot displace newer records.
        assert "obs-0000" not in controller._scout_observations
        assert json.loads(controller._scout_observations["obs-0129"]["summary_json"])["passability"] == 0
        assert json.loads(controller._scout_observations["obs-0130"]["summary_json"])["passability"] == 1
        controller._publish()

        # This subscriber joins only after all evidence has been received.
        states = []
        rig.probe.create_subscription(String, "/redline/campaign/state",
                                      lambda m: states.append(json.loads(m.data)), MAP_QOS)
        assert rig.until(lambda: any(len(s.get("scout_observations", [])) == 128 for s in states))
        late = next(s for s in states if len(s.get("scout_observations", [])) == 128)
        observations = late["scout_observations"]
        assert observations[-1]["evidence_id"] == "obs-0130"
        assert all(o["header"]["frame_id"] == "map" and o["provenance"]["status"] == 2 for o in observations)
        assert len(json.dumps(late, ensure_ascii=False).encode("utf-8")) <= 240000

        # Large existing product summaries take precedence over this optional view.
        for index in range(2):
            controller._product(InstrumentProduct(product_id=f"padding-{index}", instrument="TEST",
                target_id="BXW_RIDGE_A", summary_json=json.dumps({"padding": "x" * 110000})))
        bounded = json.loads((controller.output / "campaign_state.json").read_text())
        assert len(bounded["products"]) == 2
        assert 0 < len(bounded["scout_observations"]) < 128
        assert bounded["scout_observations"][-1]["evidence_id"] == "obs-0130"
        assert len(json.dumps(bounded, ensure_ascii=False).encode("utf-8")) <= 240000
        assert len(controller._scout_observations) == 128
    finally:
        rig.close()


def test_rover_science_is_remotely_requested_without_moving_the_crew(ros, tmp_path):
    rig = Rig(tmp_path)
    try:
        # Local work still requires arrival and completed products/custody.
        while rig.controller.campaign.task.id != "rover_libs":
            kind = rig.controller.campaign.task.kind
            rig.complete_current("CHOOSE_RIDGE" if kind == "decision" else "START")
        rig.crew_location = [285.1, -468., 0.]
        assert rig.until(lambda: rig.controller._human_position == tuple(rig.crew_location[:2]))
        remote = rig.controller.campaign.task
        assert remote.xy != tuple(rig.crew_location[:2])
        rig.controller._publish()
        snapshot = json.loads((rig.controller.output / "campaign_state.json").read_text())
        view = snapshot["task"]["presentation"]
        assert view["enabled"] and view["interaction_mode"] == "remote" and not view["arrived"]

        rig.publish_robot = False
        rig.controller._robot_receipt = -float("inf")
        response, _ = rig.command(request_id="remote-stale-robot")
        assert not response.accepted and rig.nav_count == 0
        rig.publish_robot = True
        assert rig.until(lambda: time.monotonic() - rig.controller._robot_receipt < .1)
        assert not rig.command(request_id="remote-wrong-target", target="WRONG")[0].accepted
        for task_id in ("rover_libs", "rover_dan", "drill"):
            assert rig.controller.campaign.task.id == task_id
            previous = rig.controller.campaign.index
            response, _ = rig.command(request_id="remote-" + task_id)
            assert response.accepted, response.reason
            assert rig.until(lambda: rig.controller.campaign.index > previous)
            assert rig.controller._human_position == (285.1, -468.)
            assert rig.crew_location == [285.1, -468., 0.]
        assert rig.nav_count == 1 and rig.controller.campaign.task.id == "cache"
        assert all(task in rig.controller.campaign.completed for task in ("rover_libs", "rover_dan", "drill"))
        assert len(rig.controller.campaign.product_ids) == 6

        # The next human task is local again; neither arriving nor a remote
        # command to the wrong place can credit sample delivery.
        rig.crew_location = [306., -454., 0.]
        assert rig.until(lambda: rig.controller._human_position == tuple(rig.crew_location[:2]))
        response, _ = rig.command(request_id="cache-from-field")
        assert not response.accepted and "cache" not in rig.controller.campaign.completed
        assert rig.controller.campaign.task.id == "cache"
        rig.controller.sep_alert = True
        rig.controller._publish()
        snapshot = json.loads((rig.controller.output / "campaign_state.json").read_text())
        assert snapshot["task"]["presentation"]["blocked_reason"] == "sep_alert"
        assert not snapshot["task"]["presentation"]["enabled"]
    finally:
        rig.close()

