"""S1 end to end (proje.md §17, §18 T6): SEP alarm → shelter mode within 30 s PET (FR-04),
EMERGENCY alert, ReturnToShelter, and the red line shrinking to the shelter limit.
RAD values here are a SIMULATED rise; the real sol 4190 run is scripts/run-s1-bxw.sh."""
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.executors import SingleThreadedExecutor

from redline_data.rad import write_rad_table
from redline_msgs.msg import Alert, DecisionRecord, DoseRate, MissionState, RedLine, RuleViolation
from redline_msgs.srv import ScenarioControl
from t5_fixtures import write_inputs

MAP_QOS = rclpy.qos.QoSProfile(depth=1, reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                               durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL)
EVENT_QOS = rclpy.qos.QoSProfile(depth=50, reliability=rclpy.qos.ReliabilityPolicy.RELIABLE)
STATE_QOS = rclpy.qos.QoSProfile(depth=10, reliability=rclpy.qos.ReliabilityPolicy.RELIABLE)
START = datetime(2024, 5, 20, 0, 0, 0, tzinfo=timezone.utc)
ALARM = START + timedelta(hours=8)  # SIMULATED: 5 → 40 µGy/h


def rdr_text():
    lines = ["[FILE]", "START_SOL=9999", ""]
    for k in range(0, 120, 2):
        t = START + timedelta(minutes=5 * k)
        value = 40.0 if t >= ALARM else 5.0
        lines += [f"[OBSERVATION: {k:03d}]", 'START_OBS_MARS="9999 0:00:00"',
                  f'START_OBS_UTC="{t.year}-{t.timetuple().tm_yday:03d} {t:%H:%M:%S}"', "",
                  f"[DOSIMETRY_TOTAL_DOSE_B: {k:03d}]", "", f"{value}", "",
                  f"[DOSIMETRY_TOTAL_DOSE_E: {k:03d}]", "", f"{value}", ""]
    return "\n".join(lines) + "\n"


def ring_area(polygon):
    pts = np.array([(p.x, p.y) for p in polygon.points])
    return 0.5 * float(np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1]))


@pytest.fixture
def s1(tmp_path):
    paths = write_inputs(tmp_path)
    (tmp_path / "RAD.TXT").write_text(rdr_text(), encoding="ascii")
    write_rad_table(tmp_path / "RAD.TXT", tmp_path / "env" / "rad_9999.csv", source_url="simulated://s1-test")
    scenario = tmp_path / "S1_TEST.yaml"
    scenario.write_text("id: S1_TEST\nsite: TST\nseed: 7\ntime_scale: 20\n"
                        "start: {historical_utc: '2024-05-20T07:59:00Z', pet_min: 0}\n"
                        "crew: [EV1]\nreplay: {rad: {sols: [9999], detector: E}}\n")
    rules = tmp_path / "rules.yaml"
    rules.write_text("provenance_status: SCENARIO\nrules:\n  FR-01: {evaluated: true, severity: WARNING}\n"
                     "  FR-04: {evaluated: true, window_s: 30.0, severity: EMERGENCY}\n")
    log = (tmp_path / "launch.log").open("w")
    command = ["ros2", "launch", "redline_planner", "t5_thread.launch.py", "planner:=false",
               f"python:={os.environ['REDLINE_PYTHON']}", f"scenario_file:={scenario}",
               f"env_dir:={tmp_path / 'env'}", f"rules_file:={rules}", "sep_shelter_max_min:=1.0"] + \
        [f"{k}:={v}" for k, v in paths.items()]
    started = []

    def start():  # the probe subscribes first, so one-shot events are not lost to discovery
        started.append(subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True))
        return started[0]

    yield start, tmp_path / "launch.log"
    process = started[0] if started else None
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    log.close()


def test_s1_alarm_shelter_mode_return_and_line_shrink(s1):
    start, log_path = s1
    rclpy.init()
    probe = rclpy.create_node("unreal_stand_in")
    doses, states, alerts, violations, redlines, decisions = [], [], [], [], [], []
    probe.create_subscription(DoseRate, "/env/dose_rate", doses.append, STATE_QOS)
    # Depth 10: CONTINGENCY → RETURN can follow within milliseconds (keep-last 1 would drop it).
    probe.create_subscription(MissionState, "/redline/mission/state", states.append, STATE_QOS)
    probe.create_subscription(Alert, "/redline/alerts", alerts.append, EVENT_QOS)
    probe.create_subscription(RuleViolation, "/safety/violations", violations.append, EVENT_QOS)
    probe.create_subscription(RedLine, "/redline/redline", redlines.append, MAP_QOS)
    probe.create_subscription(DecisionRecord, "/redline/decisions", decisions.append, EVENT_QOS)
    control = probe.create_client(ScenarioControl, "/redline/scenario/control")
    pose = probe.create_publisher(PoseStamped, "/crew/EV1/pose", STATE_QOS)
    executor = SingleThreadedExecutor()
    executor.add_node(probe)
    where = [42.0, 2.0]
    process = start()

    def spin(seconds, until=None):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            message = PoseStamped()
            message.header.frame_id = "map"
            message.pose.position.x, message.pose.position.y = where
            message.pose.orientation.w = 1.0
            pose.publish(message)
            executor.spin_once(timeout_sec=0.05)
            if until is not None and until():
                return True
        return until is None

    try:
        assert spin(150.0, lambda: redlines and redlines[-1].limiting_crew_id == "EV1" or process.poll() is not None)
        assert process.poll() is None, log_path.read_text()
        before = sum(ring_area(p) for p in redlines[-1].abort_regions)
        assert spin(60.0, lambda: any(d.alert for d in doses)), "no SEP alarm:\n" + log_path.read_text()
        assert spin(20.0, lambda: any(s.phase == MissionState.RETURN for s in states))
        phases = [s.phase for s in states]
        assert MissionState.CONTINGENCY in phases or any(
            d.context == "SEP_ALERT" and json.loads(d.assumptions_json)["to_phase"] == MissionState.CONTINGENCY
            for d in decisions), phases
        assert spin(10.0, lambda: any(v.rule_id == "FR-04" for v in violations))
        fr04 = [v for v in violations if v.rule_id == "FR-04"]
        assert fr04[0].severity == Alert.INFO and fr04[0].value <= 30.0, [v.text for v in fr04]
        assert any(a.code == "SEP_ALERT" and a.severity == Alert.EMERGENCY for a in alerts)
        # The alarm can only arrive once scenario_player started mission time; LOAD names the run.
        request = ScenarioControl.Request()
        request.command = ScenarioControl.Request.LOAD
        future = control.call_async(request)
        assert spin(10.0, future.done) and future.result().success
        assert future.result().run_id.endswith("-S1_TEST-7")
        # SEP mode: the line closes in to the 1-minute shelter walk.
        assert spin(10.0, lambda: redlines and sum(ring_area(p) for p in redlines[-1].abort_regions) < 0.5 * before)
        where[:] = [2.0, 2.0]  # the crew walks home
        assert spin(30.0, lambda: any(s.phase == MissionState.DEBRIEF for s in states))
        assert len(decisions) >= 3
        assert not any(v.rule_id == "FR-04" and v.severity == Alert.EMERGENCY for v in violations)
    finally:
        executor.shutdown()
        probe.destroy_node()
        rclpy.try_shutdown()
