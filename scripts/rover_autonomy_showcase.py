#!/usr/bin/env python3
"""Bounded multi-goal ROS autonomy demo. No velocity or world-truth planning input."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
import rclpy
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from rclpy.qos import QoSProfile, DurabilityPolicy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycles', type=int, default=3)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--behavior-tree', type=Path)
    parser.add_argument('--first-three',action='store_true',help='Short forward acceptance route; stop after three targets')
    args = parser.parse_args()
    if not 1 <= args.cycles <= 5:
        parser.error('cycles must be in [1,5]')
    rclpy.init()
    node = rclpy.create_node('rover_autonomy_showcase')
    client = ActionClient(node, NavigateToPose, '/rover_1/navigate_to_pose')
    state = {'physics': 0., 'physical_pose': None}
    def physical(message):
        p = message.pose.pose.position
        state['physical_pose'] = [p.x, p.y, p.z]
    subscriptions = [node.create_subscription(Clock, '/clock', lambda msg: state.update(
        physics=msg.clock.sec + msg.clock.nanosec / 1e9), 5),
        node.create_subscription(Odometry, '/redline/presentation/rover_1/odom', physical, 2)]
    status = node.create_publisher(String, '/redline/demo/navigation_status',
        QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    report = {'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'SCENARIO',
              'scope': 'ROS NavigateToPose sequential targets, physical pose is evaluation only',
              'physics_authority': 'Gazebo', 'goals': [], 'passed': False}
    route = [(145., -299., -math.pi/2), (145., -309., -math.pi/2),
             (145., -319., -math.pi/2), (155., -319., 0.),
             (155., -309., math.pi/2), (145., -299., -math.pi/2)]
    if args.first_three:route=route[:3]
    active = None
    def publish(label):
        message = String()
        message.data = json.dumps({'state': label, 'completed': sum(g.get('action_status') == 4 for g in report['goals']),
            'planned': len(route)*args.cycles, 'last_goal': report['goals'][-1] if report['goals'] else None})
        status.publish(message)
        args.out.write_text(json.dumps(report, indent=2) + '\n')
    def wait(future, seconds):
        end = time.monotonic() + seconds
        while not future.done() and time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.02)
        return future.done()
    try:
        if not client.wait_for_server(timeout_sec=30):
            raise RuntimeError('Nav2 action unavailable')
        for cycle in range(args.cycles):
            for x, y, yaw in route:
                goal = NavigateToPose.Goal()
                if args.behavior_tree:
                    goal.behavior_tree = str(args.behavior_tree.resolve())
                goal.pose.header.frame_id = 'map'
                # Map-frame target at latest TF; never mix system-wall stamp
                # with the Gazebo physics clock used by Nav2.
                goal.pose.pose.position.x, goal.pose.pose.position.y = x, y
                goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(yaw/2), math.cos(yaw/2)
                item = {'cycle': cycle+1, 'target_map_xy_m': [x, y], 'yaw_rad': yaw,
                        'started_wall_utc': datetime.now(timezone.utc).isoformat(), 'start_physics_s': state['physics']}
                report['goals'].append(item)
                started = time.monotonic()
                publish('requesting')
                request = client.send_goal_async(goal)
                if not wait(request, 10):
                    raise RuntimeError('Goal acceptance timeout')
                active = request.result()
                item['accepted'] = active.accepted
                item['acceptance_wall_s'] = time.monotonic() - started
                if not active.accepted:
                    raise RuntimeError('Nav2 rejected target')
                publish('navigating')
                result = active.get_result_async()
                if not wait(result, 180):
                    active.cancel_goal_async()
                    raise RuntimeError('Goal exceeded 180 wall seconds')
                item.update(action_status=result.result().status, duration_wall_s=time.monotonic()-started,
                            end_physics_s=state['physics'], end_physical_xyz_m=state['physical_pose'])
                if state['physical_pose']:
                    item['physical_goal_xy_error_m'] = math.dist(state['physical_pose'][:2], [x, y])
                print(json.dumps(item), flush=True)
                active = None
                publish('target reached' if item['action_status'] == 4 else 'failed')
                if item['action_status'] != 4:
                    raise RuntimeError('NavigateToPose returned status ' + str(item['action_status']))
        report['passed'] = True
        publish('complete')
    except (KeyboardInterrupt, Exception) as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        if active is not None:
            cancel = active.cancel_goal_async()
            wait(cancel, 3)
        publish('stopped')
    finally:
        report['ended_at_utc'] = datetime.now(timezone.utc).isoformat()
        args.out.write_text(json.dumps(report, indent=2) + '\n')
        node.destroy_node()
        rclpy.try_shutdown()
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
