#!/usr/bin/env python3
"""Simulation-only transient obstacle test during an already active drive.

Adds a labelled SCENARIO box to Gazebo, never a velocity, goal, map, or sensor
publisher. Nav2 can learn of it only through its simulated sensor input. The
box is removed after the measured stop, and the existing action may resume.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

import rclpy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from rclpy.qos import qos_profile_sensor_data
from tf2_ros import Buffer, TransformListener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terrain', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    module = args.workspace / 'src/redline_gazebo/scripts/prepare_world.py'
    spec = importlib.util.spec_from_file_location('world', module)
    world = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(world)
    terrain = json.loads(args.terrain.read_text())
    for tile in terrain['meshes']:
        tile['collision_uri'] = (args.terrain.parent / tile.get('collision_relative_path', tile['relative_path'])).resolve().as_uri()
    rclpy.init()
    node = rclpy.create_node('t3_transient_obstacle_probe')
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    started = time.monotonic()
    latest = {'vx': 0., 'wz': 0., 'at': 0.}
    events = []
    created = None
    process = None
    removed = False
    record = {'observed_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'SCENARIO', 'passed': False,
              'scope': 'one transient tall box, 2D scan reaction; not low-rock/3D avoidance acceptance',
              'events': events, 'physics_authority': 'Gazebo', 'events_clock': 'monotonic wall seconds from probe start'}
    def command(message):
        now = time.monotonic() - started
        latest.update(vx=message.linear.x, wz=message.angular.z, at=now)
        if process is not None and not removed and abs(message.linear.x) + abs(message.angular.z) < 1e-4:
            if not any(e['event'] == 'zero_command_received' for e in events):
                events.append({'event': 'zero_command_received', 'wall_s': now})
    def scan(message):
        if process is None or removed:
            return
        # Evaluates the same approximate XY Stop rectangle; this does not feed
        # the monitor. Lidar XY is centred at base_link in the staged model.
        inside = [value for i, value in enumerate(message.ranges)
                  if math.isfinite(value) and message.range_min <= value <= message.range_max
                  and .2 < value * math.cos(message.angle_min + i * message.angle_increment) < 2.5721
                  and abs(value * math.sin(message.angle_min + i * message.angle_increment)) < 1.5887]
        if inside and not any(e['event'] == 'scan_return_inside_stop_rectangle' for e in events):
            events.append({'event': 'scan_return_inside_stop_rectangle',
                           'wall_s': time.monotonic() - started,
                           'scan_stamp_s': message.header.stamp.sec + message.header.stamp.nanosec / 1e9,
                           'returns': len(inside), 'nearest_m': min(inside)})
    subscriptions = [node.create_subscription(Twist, '/rover_1/cmd_vel_sim', command, qos_profile_sensor_data),
                     node.create_subscription(LaserScan, '/rover_1/scan', scan, qos_profile_sensor_data)]
    service = ['gz', 'service', '-s', '/world/bxw/create', '--reqtype', 'gz.msgs.EntityFactory',
               '--reptype', 'gz.msgs.Boolean', '--timeout', '5000']
    try:
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
            if .08 < latest['vx'] <= .31 and abs(latest['wz']) < .1 and buffer.can_transform('map', 'rover_1/base_link', rclpy.time.Time()):
                break
        else:
            raise RuntimeError('No current forward drive / transform within 35 s')
        tf = buffer.lookup_transform('map', 'rover_1/base_link', rclpy.time.Time()).transform
        q = tf.rotation
        yaw = math.atan2(2 * (q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
        x, y = tf.translation.x + 3.0*math.cos(yaw), tf.translation.y + 3.0*math.sin(yaw)
        z = world.terrain_height(terrain, x, y)
        sdf = ET.Element('sdf', version='1.9')
        model = ET.SubElement(sdf, 'model', name='SCENARIO_transient_stop_probe')
        ET.SubElement(model, 'static').text = 'true'
        ET.SubElement(model, 'pose').text = f'{x} {y} {z + 1.5} 0 0 {yaw}'
        link = ET.SubElement(model, 'link', name='fixture')
        for kind in ('visual', 'collision'):
            shape = ET.SubElement(link, kind, name=kind)
            ET.SubElement(ET.SubElement(ET.SubElement(shape, 'geometry'), 'box'), 'size').text = '1 1 3.5'
        record['box_pose_map_m_rad'] = [x, y, z + 1.5, yaw]
        record['pre_insertion_command'] = dict(latest)
        request = 'sdf: ' + json.dumps(ET.tostring(sdf, encoding='unicode'))
        events.append({'event': 'creation_request_sent', 'wall_s': time.monotonic() - started})
        process = subprocess.Popen(service + ['--req', request], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.01)
            if created is None and process.poll() is not None:
                out, err = process.communicate()
                if process.returncode or 'data: true' not in out:
                    raise RuntimeError('Gazebo create failed: ' + out + err)
                created = time.monotonic() - started
                events.append({'event': 'creation_acknowledged', 'wall_s': created})
            zero = next((e for e in events if e['event'] == 'zero_command_received'), None)
            if created is not None and zero is not None and time.monotonic() - started > zero['wall_s'] + 2:
                break
        remove = subprocess.run(['gz', 'service', '-s', '/world/bxw/remove', '--reqtype', 'gz.msgs.Entity',
            '--reptype', 'gz.msgs.Boolean', '--timeout', '5000', '--req', 'name: "SCENARIO_transient_stop_probe" type: MODEL'],
            capture_output=True, text=True, timeout=8)
        removed = remove.returncode == 0 and 'data: true' in remove.stdout
        record['removed'] = removed
        events.append({'event': 'removal_acknowledged' if removed else 'removal_failed', 'wall_s': time.monotonic() - started})
        deadline = time.monotonic() + 15
        resumed = None
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
            if latest['at'] > events[-1]['wall_s'] and latest['vx'] > .02:
                resumed = time.monotonic() - started
                events.append({'event': 'forward_command_resumed', 'wall_s': resumed})
                break
        scan_event = next((e for e in events if e['event'] == 'scan_return_inside_stop_rectangle'), None)
        zero = next((e for e in events if e['event'] == 'zero_command_received'), None)
        request_event = next(e for e in events if e['event'] == 'creation_request_sent')
        record['request_to_zero_wall_s'] = zero['wall_s'] - request_event['wall_s'] if zero else None
        record['scan_receipt_to_zero_wall_s'] = zero['wall_s'] - scan_event['wall_s'] if zero and scan_event else None
        record['passed'] = bool(scan_event and zero and removed and resumed is not None
                                and 0 <= record['scan_receipt_to_zero_wall_s'] <= .5)
        record['limits'] = ['Receipt ordering bounds callback latency, not an independently synchronised sensor-to-actuator clock.',
                            'A zero command is not a physical stopping-distance/collision proof.']
    except Exception as error:
        record['error'] = str(error)
    finally:
        args.out.write_text(json.dumps(record, indent=2) + '\n')
        node.destroy_node()
        rclpy.try_shutdown()
        print(json.dumps(record, indent=2))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
