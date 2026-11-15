"""One bounded simulation-only Nav2 drive for the campaign presentation.

Requires a dedicated, untouched campaign at ready briefing (index/revision 0),
fresh physical /clock and map odometry, and an observed idle Nav2 status array.
An explicit owned-first-goal receipt can admit the *absence* of initial status
on a newly owned Gazebo graph: rclcpp_action publishes it on goal transitions.
This optional mode never overrides a received status and is consumed once.
It sends one staged-manifest goal. It never sends science/mission commands,
human poses, set_pose, Twist or time-scale changes. Keep the human at briefing.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import time
import uuid


MAX_FEED_BYTES = 64 * 1024 * 1024
MAX_FEED_RECORDS = 100_000
MAX_ODOMETRY_RECORDS = 4000
BUSY_GOAL_STATUSES = (1, 2, 3)


def owned_receipt_identity(receipt, domain_id, campaign_run_id):
    """Bind opt-in first-goal permission to one simulation owner and campaign."""
    if (not isinstance(receipt, dict)
            or receipt.get("schema") != "redline.campaign.owned-first-goal.v1"
            or type(receipt.get("domain_id")) is not int
            or receipt["domain_id"] != domain_id
            or receipt.get("campaign_run_id") != campaign_run_id
            or not isinstance(campaign_run_id, str) or not campaign_run_id
            or receipt.get("no_commands_sent") is not True
            or receipt.get("physics_authority") != "Gazebo"
            or type(receipt.get("supervisor_pid")) is not int or receipt["supervisor_pid"] <= 1
            or type(receipt.get("robot_supervisor_pid")) is not int or receipt["robot_supervisor_pid"] <= 1
            or not isinstance(receipt.get("supervisor_start_ticks"), str)
            or not receipt["supervisor_start_ticks"].isdigit()
            or not isinstance(receipt.get("gz_partition"), str)
            or not receipt["gz_partition"].startswith("redline-campaign-campaign-")):
        raise ValueError("owned first-goal receipt does not match this simulation/campaign")
    return True


def status_admits_goal(*, received, age_s, busy, owned_absence=False,
                      listening_s=0., expected_publisher=False):
    """Received state always wins; a first-goal receipt permits absence only."""
    if received:
        return math.isfinite(age_s) and 0 <= age_s < 2 and not busy
    return (owned_absence and not busy and math.isfinite(listening_s)
            and listening_s >= 2 and expected_publisher)


def validate_owned_processes(path, receipt, domain_id, *, proc_root=Path("/proc")):
    """Verify live owner PID/start time, exact session directory and ROS child."""
    directory = path.resolve().parent
    if Path(receipt.get("evidence_path", "")).resolve() != directory:
        raise ValueError("receipt must reside in its owned campaign evidence directory")
    if (directory / "supervisor.pid").read_text().strip() != str(receipt["supervisor_pid"]):
        raise ValueError("campaign supervisor identity changed")
    process_groups = [int(v) for v in (directory / "process-groups.txt").read_text().split()]
    if not process_groups or process_groups[0] != receipt["robot_supervisor_pid"]:
        raise ValueError("robot process ownership does not match the session")
    supervisor = proc_root / str(receipt["supervisor_pid"])
    # Field 22 is starttime; discard the parenthesized comm before splitting.
    start_ticks = (supervisor / "stat").read_text().rsplit(")", 1)[1].split()[19]
    if start_ticks != receipt["supervisor_start_ticks"]:
        raise ValueError("campaign supervisor PID was reused")
    command = (supervisor / "cmdline").read_bytes().decode().split("\0")
    if not any(v.endswith("run-campaign-backend.sh") for v in command):
        raise ValueError("receipt does not name the campaign backend owner")
    robot = proc_root / str(receipt["robot_supervisor_pid"])
    child_command = (robot / "cmdline").read_bytes().decode().split("\0")
    environment = dict(v.split("=", 1) for v in (robot / "environ").read_bytes().decode().split("\0") if "=" in v)
    if (not any(v.endswith("t3_supervisor.py") for v in child_command)
            or environment.get("ROS_DOMAIN_ID") != str(domain_id)
            or environment.get("GZ_PARTITION") != receipt["gz_partition"]):
        raise ValueError("robot owner/domain/physics partition no longer matches")
    if (directory / "first-goal.claim.json").exists():
        raise ValueError("owned first-goal receipt was already consumed")
    created = datetime.fromisoformat(receipt["created_at_utc"])
    if created.tzinfo is None or not 0 <= (datetime.now(timezone.utc) - created).total_seconds() <= 900:
        raise ValueError("owned first-goal receipt is expired or has no timezone")
    return True


def untouched_briefing(state):
    return (isinstance(state, dict) and state.get("schema") == "redline.campaign.v1"
            and state.get("state") == "ready" and type(state.get("task_index")) is int
            and state["task_index"] == 0 and type(state.get("revision")) is int
            and state["revision"] == 0 and isinstance(state.get("task"), dict)
            and state["task"].get("id") == "briefing" and state.get("operation_id") == "")


def staged_goal(manifest):
    if manifest.get("frame") != "map" or manifest.get("units") != "m":
        raise ValueError("staged terrain must explicitly use map metres")
    goal = manifest["goal"]
    values = [goal[name] for name in ("map_x_m", "map_y_m", "ground_z_m", "yaw_rad")]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise ValueError("staged goal needs finite numeric XYZ and yaw")
    if max(abs(v) for v in values[:3]) > 1e7:
        raise ValueError("goal outside the supported local map range")
    return tuple(float(v) for v in values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terrain", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seconds", type=float, default=95.)
    parser.add_argument("--owned-first-goal-receipt", type=Path,
                        help="Explicit one-use fresh Gazebo owner receipt; permits absent initial status only")
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 1 <= args.seconds <= 100:
        parser.error("--seconds must be in [1,100] wall seconds")
    # A caller must select the same isolated domain as the campaign explicitly.
    if "ROS_DOMAIN_ID" not in os.environ:
        parser.error("explicit ROS_DOMAIN_ID required; do not use a default graph")
    owned_receipt = None
    if args.owned_first_goal_receipt:
        if args.owned_first_goal_receipt.stat().st_size > 16000:
            parser.error("oversized first-goal receipt")
        owned_receipt = json.loads(args.owned_first_goal_receipt.read_text())
        owned_receipt_identity(owned_receipt, int(os.environ["ROS_DOMAIN_ID"]), owned_receipt.get("campaign_run_id"))
        validate_owned_processes(args.owned_first_goal_receipt, owned_receipt, int(os.environ["ROS_DOMAIN_ID"]))
    manifest = json.loads(args.terrain.read_text())
    target = staged_goal(manifest)
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out / "verification.json").exists():
        parser.error("output contains a previous verification; select a new folder")

    import rclpy
    from rclpy.action import ActionClient
    from rclpy.parameter import Parameter
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
    from nav2_msgs.action import NavigateToPose
    from nav_msgs.msg import Odometry, Path as NavPath
    from rosgraph_msgs.msg import Clock
    from action_msgs.msg import GoalStatusArray
    from action_msgs.srv import CancelGoal
    from unique_identifier_msgs.msg import UUID
    from std_msgs.msg import String
    from tf2_msgs.msg import TFMessage
    from rosidl_runtime_py.convert import message_to_ordereddict

    started = time.monotonic()
    report = {"schema": "redline.campaign.presentation-drive.v1", "passed": False,
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "SCENARIO",
              "scope": "One simulation-only staged Nav2 goal and actual Gazebo movement; no full campaign, long route or obstacle acceptance",
              "terrain": str(args.terrain.resolve()), "terrain_sha256": hashlib.sha256(args.terrain.read_bytes()).hexdigest(),
              "goal_map_xyz_yaw": target, "domain_id": os.environ["ROS_DOMAIN_ID"],
              "authority": "ROS/Gazebo/Nav2", "physics_time_source": "/clock",
              "human_pose_published": False, "science_or_mission_commands_sent": False,
              "pose_setter_used": False, "time_scale_changed": False, "navigate_goal_count": 0,
              "feed_byte_limit": MAX_FEED_BYTES, "feed_record_limit": MAX_FEED_RECORDS,
              "converter": "rosidl_runtime_py.convert.message_to_ordereddict (installed signature verified)",
              "cancel_requested": False, "cancel_acknowledged": False}
    report["owned_first_goal_mode"] = owned_receipt is not None
    if owned_receipt:
        report["owned_first_goal_receipt"] = str(args.owned_first_goal_receipt.resolve())
        report["owned_first_goal_receipt_sha256"] = hashlib.sha256(args.owned_first_goal_receipt.read_bytes()).hexdigest()
    rclpy.init()
    node = rclpy.create_node("campaign_presentation_drive_probe", parameter_overrides=[Parameter("use_sim_time", value=True)])
    durable = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
    status_qos = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
    feed_path = args.out / "ue_feed.jsonl"
    stream = feed_path.open("x", encoding="utf-8", newline="\n")
    samples = []
    state = {"campaign": None, "campaign_at": -math.inf, "clock": None, "clock_at": -math.inf,
             "odom": None, "odom_at": -math.inf, "status": None, "status_at": -math.inf,
             "path_at": -math.inf, "path_poses": 0, "feed_bytes": 0, "feed_records": 0,
             "post_goal_path_seen": False, "post_goal_max_path_poses": 0,
             "feed_truncated": False, "error": None, "own_goal_id": None}
    last_feed_at = {}
    own_handle = None
    result_future = None
    sent = None
    goal_sent_at = None
    interrupted = False

    def stop(_sig, _frame):
        nonlocal interrupted
        interrupted = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    def capture(topic, message, minimum_interval=.1):
        now = time.monotonic()
        if now - last_feed_at.get(topic, -math.inf) < minimum_interval or state["feed_truncated"]:
            return
        packet = {"op": "publish", "topic": topic, "msg": message_to_ordereddict(message),
                  "_redline_elapsed_sec": now-started}
        text = json.dumps(packet, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
        size = len(text.encode("utf-8"))
        if state["feed_bytes"] + size > MAX_FEED_BYTES or state["feed_records"] >= MAX_FEED_RECORDS:
            state["feed_truncated"] = True
            return
        stream.write(text)
        stream.flush()
        state["feed_bytes"] += size
        state["feed_records"] += 1
        last_feed_at[topic] = now

    def campaign(message):
        try:
            if len(message.data) > 240000:
                raise ValueError("oversized campaign")
            decoded = json.loads(message.data)
            if not isinstance(decoded, dict):
                raise ValueError("campaign is not an object")
            state["campaign"], state["campaign_at"] = decoded, time.monotonic()
            capture("/redline/campaign/state", message, .2)
        except (ValueError, TypeError) as error:
            state["error"] = "invalid campaign stream: " + str(error)

    def clock(message):
        if state["clock"] is None or message.clock != state["clock"]:
            state["clock"], state["clock_at"] = deepcopy(message.clock), time.monotonic()
        capture("/clock", message)

    def odometry(message):
        p, q = message.pose.pose.position, message.pose.pose.orientation
        xyz = (p.x, p.y, p.z)
        norm = q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w
        if message.header.frame_id != "map" or message.child_frame_id != "rover_1/base_link" or not all(math.isfinite(v) and abs(v) <= 1e7 for v in xyz) or not math.isfinite(norm) or abs(norm-1) > .01:
            state["error"] = "invalid physical map odometry"
            return
        source_s = message.header.stamp.sec + message.header.stamp.nanosec*1e-9
        if state["odom"] is None or state["odom"]["physics_s"] != source_s:
            record = {"wall_s": time.monotonic()-started, "physics_s": source_s, "map_xyz_m": xyz}
            state["odom"], state["odom_at"] = record, time.monotonic()
            if len(samples) < MAX_ODOMETRY_RECORDS:
                # Match the bounded feed rather than accumulating 60 Hz indefinitely.
                if not samples or record["wall_s"]-samples[-1]["wall_s"] >= .08:
                    samples.append(record)
        capture("/redline/presentation/rover_1/odom", message)

    def nav_status(message):
        if len(message.status_list) > 64 or any(s.status not in range(7) or len(s.goal_info.goal_id.uuid) != 16 for s in message.status_list):
            state["error"] = "invalid Nav2 status array"
            return
        state["status"], state["status_at"] = message, time.monotonic()
        capture("/rover_1/navigate_to_pose/_action/status", message, .2)

    def nav_path(message):
        if message.header.frame_id != "map" or len(message.poses) > 4096:
            state["error"] = "invalid or oversized Nav2 map path"
            return
        for pose in message.poses:
            p = pose.pose.position
            if pose.header.frame_id not in ("", "map") or not all(math.isfinite(v) and abs(v) <= 1e7 for v in (p.x, p.y, p.z)):
                state["error"] = "invalid Nav2 path point/frame"
                return
        state["path_at"], state["path_poses"] = time.monotonic(), len(message.poses)
        if goal_sent_at is not None and message.poses:
            state["post_goal_path_seen"] = True
            state["post_goal_max_path_poses"] = max(state["post_goal_max_path_poses"], len(message.poses))
        capture("/rover_1/plan", message, .2)

    subscriptions = [
        node.create_subscription(String, "/redline/campaign/state", campaign, durable),
        node.create_subscription(Clock, "/clock", clock, qos_profile_sensor_data),
        node.create_subscription(Odometry, "/redline/presentation/rover_1/odom", odometry, 10),
        node.create_subscription(NavPath, "/rover_1/plan", nav_path, 10),
        node.create_subscription(GoalStatusArray, "/rover_1/navigate_to_pose/_action/status", nav_status, status_qos),
    ]
    # Actual presentation support streams make the recorded envelopes useful to
    # the existing offline bridge (including wheel/dust animation), not fake data.
    for typ, topic, qos, interval in (
            (Clock, "/redline/mission/clock", 10, .1),
            (String, "/redline/presentation/scene", 10, .1),
            (TFMessage, "/redline/bridge/tf_static_snapshot", durable, 0),
            (String, "/redline/bridge/tf_static_snapshot_status", durable, 0)):
        subscriptions.append(node.create_subscription(typ, topic, lambda msg, t=topic, i=interval: capture(t, msg, i), qos))
    client = ActionClient(node, NavigateToPose, "/rover_1/navigate_to_pose")
    cancel_client = node.create_client(CancelGoal, "/rover_1/navigate_to_pose/_action/cancel_goal")

    def busy_foreign():
        if state["status"] is None:
            return False
        return any(s.status in BUSY_GOAL_STATUSES and list(s.goal_info.goal_id.uuid) != state["own_goal_id"] for s in state["status"].status_list)

    def spin_until(predicate, seconds, monitor=False):
        deadline = time.monotonic()+seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.03)
            if interrupted:
                raise InterruptedError("diagnostic interrupted; own goal cancellation requested")
            if state["error"]:
                raise RuntimeError(state["error"])
            if monitor and (not untouched_briefing(state["campaign"]) or time.monotonic()-state["campaign_at"] > 2):
                raise RuntimeError("campaign changed or became stale during diagnostic")
            if monitor and owned_receipt and state["campaign"].get("run_id") != owned_receipt["campaign_run_id"]:
                raise RuntimeError("owned campaign run identity changed during diagnostic")
            if monitor and busy_foreign():
                raise RuntimeError("another active Nav2 goal appeared; refusing competition")
            if predicate():
                return
        raise TimeoutError("bounded presentation drive condition timed out")

    def fresh_preflight():
        now = time.monotonic()
        owned_absence = bool(owned_receipt and state["campaign"] and
                             state["campaign"].get("run_id") == owned_receipt["campaign_run_id"])
        publisher_expected = False
        if owned_absence and state["status"] is None:
            publishers = node.get_publishers_info_by_topic("/rover_1/navigate_to_pose/_action/status")
            publisher_expected = (len(publishers) == 1 and publishers[0].node_name == "bt_navigator"
                                  and publishers[0].node_namespace == "/rover_1"
                                  and publishers[0].qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL
                                  and publishers[0].qos_profile.reliability == ReliabilityPolicy.RELIABLE)
        return (client.server_is_ready() and untouched_briefing(state["campaign"])
                and now-state["campaign_at"] < 2 and now-state["clock_at"] < 1
                and now-state["odom_at"] < 1
                and status_admits_goal(received=state["status"] is not None,
                    age_s=now-state["status_at"], busy=busy_foreign(), owned_absence=owned_absence,
                    listening_s=now-started, expected_publisher=publisher_expected))

    try:
        spin_until(fresh_preflight, 15)
        # Reject an accidental large route before issuing anything. This is the
        # short presentation probe only, not the long-distance autonomy test.
        initial = deepcopy(state["odom"])
        distance = math.hypot(target[0]-initial["map_xyz_m"][0], target[1]-initial["map_xyz_m"][1])
        if not 3 < distance <= 20:
            raise RuntimeError(f"staged diagnostic goal must be 3–20 m away; found {distance:.3f} m")
        if not fresh_preflight():
            raise RuntimeError("preflight guards changed before dispatch")
        if owned_receipt:
            owned_receipt_identity(owned_receipt, int(os.environ["ROS_DOMAIN_ID"]), state["campaign"].get("run_id"))
            validate_owned_processes(args.owned_first_goal_receipt, owned_receipt, int(os.environ["ROS_DOMAIN_ID"]))
        report["preflight"] = {"campaign_run_id": state["campaign"]["run_id"], "task": "briefing", "revision": 0,
                               "no_executing_nav2_goals_observed": True,
                               "status_basis": "actual received idle status" if state["status"] is not None else "owned fresh graph; no status ever received; one expected reliable transient publisher",
                               "goal_distance_m": distance,
                               "initial_physical_pose": initial, "physics_stamp": message_to_ordereddict(state["clock"])}
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = deepcopy(state["clock"])
        goal.pose.pose.position.x, goal.pose.pose.position.y, goal.pose.pose.position.z = target[:3]
        goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(target[3]/2), math.cos(target[3]/2)
        goal_sent_at = time.monotonic()
        # Keep a known unique ID even if the goal response is delayed; timeout
        # cleanup can cancel only this request without cancel-all semantics.
        goal_id = UUID(uuid=list(uuid.uuid4().bytes))
        state["own_goal_id"] = [int(value) for value in goal_id.uuid]
        report["goal_uuid"] = state["own_goal_id"]
        if owned_receipt:
            claim = args.owned_first_goal_receipt.resolve().parent / "first-goal.claim.json"
            with claim.open("x", encoding="utf-8") as claim_stream:
                json.dump({"campaign_run_id": state["campaign"]["run_id"], "goal_uuid": state["own_goal_id"],
                           "created_at_utc": datetime.now(timezone.utc).isoformat(),
                           "scope": "Consumed before send; no retry/reuse even after failed acceptance"}, claim_stream, indent=2)
            report["owned_first_goal_claim"] = str(claim)
        report["navigate_goal_count"] = 1
        sent = client.send_goal_async(goal, goal_uuid=goal_id)
        spin_until(sent.done, 5)
        own_handle = sent.result()
        if own_handle is None or not own_handle.accepted:
            raise RuntimeError("Nav2 rejected the diagnostic goal")
        if list(own_handle.goal_id.uuid) != state["own_goal_id"]:
            raise RuntimeError("unexpected goal UUID in acceptance response")
        result_future = own_handle.get_result_async()
        spin_until(result_future.done, max(.1, args.seconds-(time.monotonic()-goal_sent_at)), monitor=True)
        wrapped = result_future.result()
        report.update(action_status=int(wrapped.status), error_code=int(wrapped.result.error_code), error_message=wrapped.result.error_msg)
        # Drain the actual resulting pose/status once; do not invent a goal pose.
        end = time.monotonic()+.6
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.03)
        final = state["odom"]
        moved = math.dist(initial["map_xyz_m"][:2], final["map_xyz_m"][:2])
        goal_error = math.dist(target[:2], final["map_xyz_m"][:2])
        checks = {"nav2_status_succeeded": wrapped.status == 4, "nav2_error_zero": wrapped.result.error_code == 0,
                  "actual_physical_movement_over_3m": moved > 3,
                  "actual_post_goal_path_observed": state["post_goal_path_seen"],
                  "campaign_stayed_ready_briefing": untouched_briefing(state["campaign"]),
                  "fresh_final_physical_pose": time.monotonic()-state["odom_at"] < 1,
                  "single_goal_only": report["navigate_goal_count"] == 1,
                  "feed_complete_within_bounds": not state["feed_truncated"]}
        report.update(checks=checks, passed=all(checks.values()), displacement_m=moved, physical_goal_error_m=goal_error,
                      final_physical_pose=final, observed_plan_pose_count=state["post_goal_max_path_poses"])
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        report["guard_observations"] = {"campaign": state["campaign"], "status_received": state["status"] is not None,
                                        "busy_foreign": busy_foreign(), "odom_received": state["odom"] is not None,
                                        "clock_received": state["clock"] is not None}
    finally:
        if report["navigate_goal_count"] and (result_future is None or not result_future.done()):
            report["cancel_requested"] = True
            try:
                if own_handle is not None:
                    cancelled = own_handle.cancel_goal_async()
                else:
                    cancel = CancelGoal.Request()
                    cancel.goal_info.goal_id = UUID(uuid=state["own_goal_id"])
                    if not cancel_client.wait_for_service(timeout_sec=1):
                        raise RuntimeError("cancel service unavailable after goal-response timeout")
                    cancelled = cancel_client.call_async(cancel)
                deadline = time.monotonic()+5
                while not cancelled.done() and time.monotonic() < deadline:
                    rclpy.spin_once(node, timeout_sec=.03)
                if cancelled.done():
                    answer = cancelled.result()
                    report["cancel_acknowledged"] = bool(answer and any(list(g.goal_id.uuid) == state["own_goal_id"] for g in answer.goals_canceling))
                if result_future is not None:
                    deadline = time.monotonic()+3
                    while not result_future.done() and time.monotonic() < deadline:
                        rclpy.spin_once(node, timeout_sec=.03)
                    if result_future.done():
                        report["post_cancel_action_status"] = int(result_future.result().status)
            except Exception as error:
                report["cancel_error"] = str(error)
        # A cancel response is only acceptance; measured stop is not asserted.
        report["measured_stop_claimed"] = False
        stream.close()
        report.update(ended_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_wall_s=time.monotonic()-started,
                      goal_wall_deadline_s=args.seconds, feed_bytes=state["feed_bytes"], feed_records=state["feed_records"],
                      feed_truncated=state["feed_truncated"], feed_sha256=hashlib.sha256(feed_path.read_bytes()).hexdigest())
        (args.out/"physical_odometry.json").write_text(json.dumps(samples, indent=2, allow_nan=False)+"\n")
        (args.out/"verification.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+"\n")
        client.destroy()
        node.destroy_client(cancel_client)
        node.destroy_node()
        rclpy.try_shutdown()
    print(json.dumps(report, ensure_ascii=False, allow_nan=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
