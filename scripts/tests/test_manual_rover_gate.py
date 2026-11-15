"""Real DDS input/state/output test in an isolated ROS domain (no Gazebo)."""
import importlib.util
from pathlib import Path
import time

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from lifecycle_msgs.srv import GetState

spec = importlib.util.spec_from_file_location('manual_gate', Path(__file__).parents[1] / 'manual_rover_gate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_manual_gate_requires_exclusive_mode_and_stops_on_loss_invalid_input():
    rclpy.init()
    peer = rclpy.create_node('manual_gate_test', namespace='manual_test')
    gate = module.ManualGate('manual_test')
    current = {'id': 3}
    def state(request, response):
        response.current_state.id = current['id']
        return response
    services = [peer.create_service(GetState, name + '/get_state', state)
                for name in ('controller_server', 'behavior_server', 'bt_navigator')]
    values = []
    sub = peer.create_subscription(Twist, 'cmd_vel_nav', lambda m: values.append((m.linear.x, m.angular.z, time.monotonic())), 10)
    pub = peer.create_publisher(TwistStamped, '/redline/manual/manual_test/cmd_vel', 1)
    def spin(seconds, send=False, bad=False):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if send:
                message = TwistStamped()
                message.header.frame_id = 'manual_test/base_link'
                message.header.stamp = peer.get_clock().now().to_msg()
                message.twist.linear.x = -.8
                message.twist.angular.z = .9
                if bad:
                    message.twist.linear.y = float('nan')
                pub.publish(message)
            rclpy.spin_once(peer, timeout_sec=.005)
            rclpy.spin_once(gate, timeout_sec=.005)
    try:
        spin(1.2, True)
        assert values and all(v[:2] == (0., 0.) for v in values)
        current['id'] = 2
        spin(.8, True)
        assert values[-1][:2] == (-.3, .3)
        released = time.monotonic()
        spin(.45)
        assert values[-1][:2] == (0., 0.)
        assert next(v[2] for v in values if v[2] > released and v[:2] == (0., 0.)) - released <= .35
        spin(.2, True)
        assert values[-1][:2] == (-.3, .3)
        spin(.2, True, True)
        assert values[-1][:2] == (0., 0.)
        current['id'] = 3
        spin(.8, True)
        assert values[-1][:2] == (0., 0.)
    finally:
        gate.destroy_node()
        peer.destroy_node()
        rclpy.try_shutdown()
