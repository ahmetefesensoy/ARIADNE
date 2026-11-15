"""T5 thread end to end: `ros2 launch redline_planner t5_thread.launch.py` with the
installed executables. A probe plays Unreal: it publishes the EV1 pose and a
robot observation, and reads the red line, tiles and margins (proje.md §18 T5)."""
import json
import math
import os
import signal
import subprocess
import time

import numpy as np
import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.executors import SingleThreadedExecutor

from redline_core.cells import OBSERVATION_SCHEMA
from redline_core.fieldtile import decode_tile
from redline_msgs.msg import CellDelta, CrewState, EvidenceRecord, FieldTile, MarginField, Provenance, RedLine
from t5_fixtures import SHAPE, flat_index, spin_until, write_inputs

MAP_QOS = rclpy.qos.QoSProfile(depth=1, reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                               durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL)
EVENT_QOS = rclpy.qos.QoSProfile(depth=50, reliability=rclpy.qos.ReliabilityPolicy.RELIABLE)
STATE_QOS = rclpy.qos.QoSProfile(depth=10, reliability=rclpy.qos.ReliabilityPolicy.RELIABLE)


@pytest.fixture
def thread(tmp_path):
    paths = write_inputs(tmp_path)
    log = (tmp_path / "launch.log").open("w")
    command = ["ros2", "launch", "redline_planner", "t5_thread.launch.py", "time_scale:=30.0", "planner:=false",
               f"python:={os.environ['REDLINE_PYTHON']}"] + [f"{k}:={v}" for k, v in paths.items()]
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    yield process, tmp_path / "launch.log"
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    log.close()


def test_pose_drives_a_live_line_and_an_observation_changes_the_field(thread):
    process, log_path = thread
    rclpy.init()
    probe = rclpy.create_node("unreal_stand_in")
    redlines, tiles, margins, deltas, states = [], [], [], [], []
    probe.create_subscription(RedLine, "/redline/redline", redlines.append, MAP_QOS)
    probe.create_subscription(FieldTile, "/redline/tiles/margin_min", tiles.append, MAP_QOS)
    probe.create_subscription(MarginField, "/redline/margin/EV1", margins.append, MAP_QOS)
    probe.create_subscription(CellDelta, "/redline/cells/delta", deltas.append, EVENT_QOS)
    probe.create_subscription(CrewState, "/crew/EV1/state", states.append, STATE_QOS)
    pose = probe.create_publisher(PoseStamped, "/crew/EV1/pose", STATE_QOS)
    evidence = probe.create_publisher(EvidenceRecord, "/redline/evidence", EVENT_QOS)
    executor = SingleThreadedExecutor()
    executor.add_node(probe)

    def send_pose(x, y):
        message = PoseStamped()
        message.header.frame_id = "map"
        message.pose.position.x, message.pose.position.y = x, y
        message.pose.orientation.w = 1.0
        pose.publish(message)

    def spin(seconds, until=None, walk_at=None):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if walk_at is not None:
                send_pose(*walk_at)
            executor.spin_once(timeout_sec=0.05)
            if until is not None and until():
                return True
        return until is None

    try:
        started = spin(150.0, lambda: redlines and tiles and margins or process.poll() is not None)
        assert process.poll() is None, log_path.read_text()
        assert started, "no red line within 150 s:\n" + log_path.read_text()
        # Before Unreal poses EV1: start state, no position.
        assert math.isnan(redlines[-1].margin_now_min) and redlines[-1].limiting_crew_id == ""
        tile = tiles[-1]
        decoded = decode_tile(bytes(tile.png), tile.scale, tile.offset, tile.nodata_byte)
        assert decoded.shape == SHAPE

        # EV1 egress 20 m east of the habitat; PET runs at 30x, so the margin falls ~0.5 min per second.
        assert spin(20.0, lambda: states and redlines[-1].limiting_crew_id == "EV1", walk_at=(22.0, 2.0))
        first = redlines[-1].margin_now_min
        assert 0 < first < 70.0  # standing consumes less than the nominal walk that sized the start
        spin(4.0, walk_at=(22.0, 2.0))
        later = redlines[-1].margin_now_min
        assert later < first - 0.5, (first, later)

        # A robot observation east of the habitat: CellDelta, then a faster, surer field there.
        far, mirror = flat_index(82.0, 2.0), flat_index(-78.0, 2.0)
        before = np.asarray(margins[-1].margin_min)
        assert before[far] == pytest.approx(before[mirror], abs=1e-3)
        record = EvidenceRecord()
        record.header.frame_id = "map"
        record.evidence_id = "ev-test-1"
        record.source = "unreal_stand_in"
        record.provenance.status = Provenance.SIMULATED
        record.pose.pose.position.x, record.pose.pose.position.y = 82.0, 2.0
        record.summary_json = json.dumps({"cell_observation": {"schema": OBSERVATION_SCHEMA, "state": "DETECTED",
                                                               "radius_m": 40.0}})
        evidence.publish(record)
        assert spin(10.0, lambda: deltas, walk_at=(22.0, 2.0))
        count = len(margins)
        assert spin(10.0, lambda: len(margins) > count + 1, walk_at=(22.0, 2.0))
        after = np.asarray(margins[-1].margin_min)
        assert after[far] > after[mirror] + 0.05
    finally:
        executor.shutdown()
        probe.destroy_node()
        rclpy.try_shutdown()
