#!/usr/bin/env python3
"""Read-only wall/simulation timing and Nav2 command-stream evidence."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry, Path as NavPath
from geometry_msgs.msg import Twist


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=45)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not 5 <= args.seconds <= 300:
        parser.error('seconds must be in [5,300]')
    rclpy.init()
    node = rclpy.create_node('t3_timing_probe')
    counts = Counter()
    samples = []
    commands = {}
    first = {}
    latest = {}
    started = time.monotonic()
    clock = []
    def receive(topic, message):
        now = time.monotonic() - started
        counts[topic] += 1
        first.setdefault(topic, now)
        latest[topic] = now
        if isinstance(message, Clock):
            stamp = message.clock.sec + message.clock.nanosec / 1e9
            if not clock or now - clock[-1]['wall_s'] >= .25:
                clock.append({'wall_s': now, 'sim_s': stamp})
        elif isinstance(message, Twist):
            value = commands.setdefault(topic, {'max_abs_vx_mps': 0., 'max_abs_wz_radps': 0., 'nonzero': 0})
            value['max_abs_vx_mps'] = max(value['max_abs_vx_mps'], abs(message.linear.x))
            value['max_abs_wz_radps'] = max(value['max_abs_wz_radps'], abs(message.angular.z))
            value['nonzero'] += int(abs(message.linear.x) + abs(message.angular.z) > 1e-4)
        elif isinstance(message, Odometry):
            if not samples or now - samples[-1]['wall_s'] >= .25:
                samples.append({'wall_s': now, 'odom_xy_m': [message.pose.pose.position.x, message.pose.pose.position.y]})
    streams = [('/clock', Clock), ('/rover_1/scan', LaserScan), ('/rover_1/odom', Odometry),
               ('/rover_1/plan', NavPath)]
    streams += [('/rover_1/' + name, Twist) for name in ('cmd_vel_nav', 'cmd_vel_gated', 'cmd_vel', 'cmd_vel_sim')]
    subscriptions = [node.create_subscription(kind, topic, lambda msg, t=topic: receive(t, msg),
                                              qos_profile_sensor_data) for topic, kind in streams]
    try:
        while time.monotonic() - started < args.seconds:
            rclpy.spin_once(node, timeout_sec=.05)
    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.monotonic() - started
        resets = any(b['sim_s'] < a['sim_s'] for a, b in zip(clock, clock[1:]))
        rtf = ((clock[-1]['sim_s'] - clock[0]['sim_s']) / (clock[-1]['wall_s'] - clock[0]['wall_s'])
               if len(clock) > 1 and not resets else None)
        report = {'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'read_only': True,
                  'duration_wall_s': elapsed, 'clock_reset': resets, 'real_time_factor': rtf,
                  'topic_counts': dict(counts), 'command_summary': commands, 'clock_samples': clock,
                  'odom_samples': samples, 'received_wall_hz': {
                      topic: (count - 1) / (latest[topic] - first[topic])
                      for topic, count in counts.items() if count > 1 and latest[topic] > first[topic]},
                  'limits': ['Observed receipt rates can include transport losses; RTF uses actual /clock timestamps.',
                             'No publisher or navigation action client; no goal sent by this probe.']}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + '\n')
        node.destroy_node()
        rclpy.try_shutdown()
        print(json.dumps({key: value for key, value in report.items() if key not in ('clock_samples', 'odom_samples')}, indent=2))


if __name__ == '__main__':
    main()
