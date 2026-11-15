#!/usr/bin/env python3
"""Pause autonomous lifecycle ownership, keep only sensing/map/safety chain live."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import time
import rclpy
from nav2_msgs.srv import ManageLifecycleNodes
from lifecycle_msgs.srv import GetState, ChangeState
from rcl_interfaces.srv import SetParameters
from rclpy.parameter import Parameter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['manual', 'auto'], default='manual')
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('prepare_manual_rover')
    record = {'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'mode': args.mode, 'passed': False, 'states': {}}
    def call(kind, service, request):
        client = node.create_client(kind, service)
        if not client.wait_for_service(timeout_sec=25):
            raise RuntimeError('Missing service ' + service)
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=20)
        if not future.done() or future.result() is None:
            raise RuntimeError('Service failed ' + service)
        result = future.result()
        node.destroy_client(client)
        return result
    try:
        if args.mode == 'auto':
            for name in ('bt_navigator', 'behavior_server', 'controller_server', 'collision_monitor',
                         'velocity_smoother', 'planner_server', 'map_server'):
                state = call(GetState, '/rover_1/' + name + '/get_state', GetState.Request()).current_state.id
                if state == 3:
                    request = ChangeState.Request()
                    request.transition.id = 4
                    if not call(ChangeState, '/rover_1/' + name + '/change_state', request).success:
                        raise RuntimeError('Cannot deactivate dependency ' + name)
            request = ManageLifecycleNodes.Request()
            request.command = ManageLifecycleNodes.Request.RESUME
            if not call(ManageLifecycleNodes, '/rover_1/lifecycle_manager_navigation/manage_nodes', request).success:
                raise RuntimeError('Cannot resume autonomous lifecycle group')
            for name in ('bt_navigator', 'controller_server', 'behavior_server', 'map_server', 'velocity_smoother', 'collision_monitor'):
                state = call(GetState, '/rover_1/' + name + '/get_state', GetState.Request()).current_state.id
                record['states'][name] = state
                if state != 3:
                    raise RuntimeError('Auto dependency inactive: ' + name)
            record['passed'] = True
            return 0
        request = ManageLifecycleNodes.Request()
        request.command = ManageLifecycleNodes.Request.PAUSE
        if not call(ManageLifecycleNodes, '/rover_1/lifecycle_manager_navigation/manage_nodes', request).success:
            raise RuntimeError('Cannot pause autonomous lifecycle group')
        # Pause stops controller/BT/behavior and their bonds as one transaction.
        # Keep map, smoother and collision monitor active for the manual chain.
        for name in ('map_server', 'velocity_smoother', 'collision_monitor'):
            request = ChangeState.Request()
            request.transition.id = 3
            if not call(ChangeState, '/rover_1/' + name + '/change_state', request).success:
                raise RuntimeError('Cannot activate manual dependency ' + name)
        request = SetParameters.Request()
        request.parameters = [Parameter('min_velocity', value=[-.3, 0., -.3]).to_parameter_msg()]
        response = call(SetParameters, '/rover_1/velocity_smoother/set_parameters', request)
        if not response.results or not all(result.successful for result in response.results):
            raise RuntimeError('Cannot enable bounded reverse input')
        # Wait past the normal lifecycle bond timeout, then confirm ownership.
        end = time.monotonic() + 5
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.1)
        for name, expected in [('bt_navigator', 2), ('controller_server', 2), ('behavior_server', 2),
                               ('map_server', 3), ('velocity_smoother', 3), ('collision_monitor', 3)]:
            state = call(GetState, '/rover_1/' + name + '/get_state', GetState.Request()).current_state.id
            record['states'][name] = state
            if state != expected:
                raise RuntimeError('Unexpected lifecycle state ' + name + ': ' + str(state))
        record['passed'] = True
    except Exception as error:
        record['error'] = str(error)
    finally:
        Path('test-results/' + args.mode + '-rover-mode.json').write_text(json.dumps(record, indent=2) + '\n')
        node.destroy_node()
        rclpy.try_shutdown()
        print(json.dumps(record, indent=2))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
