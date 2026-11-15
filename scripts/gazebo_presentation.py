#!/usr/bin/env python3
"""Gazebo-authoritative display pose and bounded simulation time controls.

Physical world pose is display-only: never /tf, /odom, EKF or Nav2 input. The
CLI transport preserves model names; Pose_V->TFMessage loses those names in
this installed bridge, so array order is deliberately not used as identity.
"""
from collections import deque
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time

import rclpy
from rclpy.clock import Clock, ClockType
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock as ClockMessage
from std_msgs.msg import Float64, String


def body_record(value):
    poses = [pose for pose in value.get('pose', []) if pose.get('name') == 'rover_1']
    if len(poses) != 1:
        raise ValueError('Missing/ambiguous rover model')
    pose = poses[0]
    p = pose.get('position', {})
    q = pose.get('orientation', {})
    xyz = [float(p.get(axis, 0)) for axis in ('x', 'y', 'z')]
    quat = [float(q.get(axis, 1 if axis == 'w' else 0)) for axis in ('x', 'y', 'z', 'w')]
    stamp = value.get('header', {}).get('stamp', {})
    sec, nano = int(stamp.get('sec', 0)), int(stamp.get('nsec', 0))
    if not all(math.isfinite(number) for number in xyz + quat) or sec < 0 or not 0 <= nano < 1_000_000_000:
        raise ValueError('Invalid physical pose/stamp')
    norm = sum(number*number for number in quat)
    if abs(norm - 1) > .001:
        raise ValueError('Invalid physical orientation')
    return sec, nano, xyz, quat


def stream(stream, pending):
    decoder = json.JSONDecoder()
    buffer = ''
    for line in stream:
        buffer += line
        if len(buffer) > 2_000_000:
            raise ValueError('Oversized Gazebo record')
        try:
            value, end = decoder.raw_decode(buffer.lstrip())
        except json.JSONDecodeError:
            continue
        buffer = buffer.lstrip()[end:].lstrip()
        try:
            body_record(value)
            record = value
        except ValueError:
            continue
        try:
            pending.put_nowait(record)
        except queue.Full:
            try:
                pending.get_nowait()
            except queue.Empty:
                pass
            pending.put_nowait(record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--physics-step', type=float, choices=[.001, .002], default=.001)
    parser.add_argument('--read-only',action='store_true',help='No time-control subscription or physics commands')
    parser.add_argument('--report-out',type=Path,default=Path('test-results/gazebo-presentation-live.json'))
    args, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    node = rclpy.create_node('gazebo_presentation_adapter')
    pending = queue.Queue(maxsize=2)
    process = subprocess.Popen(['gz', 'topic', '-e', '-t', '/world/bxw/pose/info', '--json-output'],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, start_new_session=True)
    threading.Thread(target=stream, args=(process.stdout, pending), daemon=True).start()
    pub = node.create_publisher(Odometry, '/redline/presentation/rover_1/odom', 2)
    scene_pub = node.create_publisher(String, '/redline/presentation/scene', 2)
    status = node.create_publisher(String, '/redline/simulation/time_status', 1)
    clock_samples = deque(maxlen=2100)
    requested = [1.0]
    last_command = [None]
    observed = []
    def clock(message):
        now = time.monotonic()
        if not clock_samples or now - clock_samples[-1][0] >= .01:
            clock_samples.append((now, message.clock.sec + message.clock.nanosec / 1e9))
    clock_sub = node.create_subscription(ClockMessage, '/clock', clock, 5)
    def scale(message):
        if not math.isfinite(message.data) or message.data not in (1., 2., 4.):
            return
        if last_command[0] is not None and last_command[0].poll() is None:
            return
        requested[0] = message.data
        # Does not change max_step_size, gravity, forces or ROS velocity limits.
        last_command[0] = subprocess.Popen(['gz', 'service', '-s', '/world/bxw/set_physics',
            '--reqtype', 'gz.msgs.Physics', '--reptype', 'gz.msgs.Boolean', '--timeout', '3000',
            '--req', 'real_time_factor: ' + str(message.data) + ' max_step_size: ' + str(args.physics_step)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    scale_sub = None if args.read_only else node.create_subscription(Float64, '/redline/simulation/time_scale', scale, 1)
    def tick():
        record = None
        while True:
            try:
                record = pending.get_nowait()
            except queue.Empty:
                break
        if record is None:
            return
        sec, nano, xyz, quat = body_record(record)
        msg = Odometry()
        msg.header.frame_id = 'map'
        msg.child_frame_id = 'rover_1/base_link'
        msg.header.stamp.sec, msg.header.stamp.nanosec = sec, nano
        msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z = xyz
        msg.pose.pose.orientation.x, msg.pose.pose.orientation.y, msg.pose.pose.orientation.z, msg.pose.pose.orientation.w = quat
        pub.publish(msg)
        wheels = [pose for pose in record.get('pose', [])
                  if pose.get('name') in ('wheel_fl_link','wheel_ml_link','wheel_rl_link',
                                          'wheel_fr_link','wheel_mr_link','wheel_rr_link')]
        moving = [pose for pose in record.get('pose', []) if pose.get('name','').startswith('SCENARIO_moving_')]
        for pose in wheels+moving:
            pose['position'] = {axis: float(pose.get('position',{}).get(axis,0)) for axis in ('x','y','z')}
            pose['orientation'] = {axis: float(pose.get('orientation',{}).get(axis,1 if axis=='w' else 0)) for axis in ('x','y','z','w')}
        scene = String()
        scene.data = json.dumps({'status':'SIMULATED', 'physics_stamp_s':sec+nano/1e9,
            'scope':'Gazebo joint-relative wheel transforms; display-only, no TF/Nav2 output',
            'wheels':wheels, 'moving_obstacles':moving})
        scene_pub.publish(scene)
        if len(observed) < 5:
            observed.append({'physics_stamp_sec': sec + nano/1e9, 'map_xyz_m': xyz, 'quaternion_xyzw': quat})
    def report():
        now = time.monotonic()
        while len(clock_samples) > 2 and now - clock_samples[0][0] > 2:
            clock_samples.popleft()
        factor = None
        if len(clock_samples) > 1:
            a, b = clock_samples[0], clock_samples[-1]
            factor = (b[1] - a[1]) / (b[0] - a[0])
        value = {'status': 'SIMULATED', 'requested_factor': requested[0], 'actual_factor': factor,
                 'physics_step_size_s': args.physics_step, 'pose_source': 'Gazebo named rover_1 model; display only',
                 'physics_authority': 'Gazebo', 'not_navigation_input': True}
        msg = String()
        msg.data = json.dumps(value)
        status.publish(msg)
        args.report_out.parent.mkdir(parents=True,exist_ok=True)
        args.report_out.write_text(json.dumps({**value,
            'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'first_observed_source_poses': observed}, indent=2) + '\n')
    steady = Clock(clock_type=ClockType.STEADY_TIME)
    timer = node.create_timer(1/60, tick, clock=steady)
    report_timer = node.create_timer(1., report, clock=steady)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        import os
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
