#!/usr/bin/env python3
"""Exclusive simulation keyboard adapter upstream of smoother/collision monitor.

Requires Nav2 controller, behavior server and navigator INACTIVE. It cannot
enable that mode itself. Missing state, stale/future/invalid input or transport
loss produces zero. Gazebo's existing downstream steady watchdog also remains.
"""
import math
import time
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped
from lifecycle_msgs.srv import GetState


class ManualGate(Node):
    def __init__(self, namespace='rover_1'):
        super().__init__('manual_rover_gate', namespace=namespace)
        self.value = (0., 0.)
        self.received = None
        self.states = {}
        self.state_clients = {name: self.create_client(GetState, name + '/get_state')
                        for name in ('controller_server', 'behavior_server', 'bt_navigator')}
        self.pending = {}
        self.publisher = self.create_publisher(Twist, 'cmd_vel_nav', 1)
        self.subscription = self.create_subscription(TwistStamped,
            '/redline/manual/' + namespace + '/cmd_vel', self.command, 1)
        steady = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(.05, self.tick, clock=steady)
        self.poll_timer = self.create_timer(.25, self.poll_states, clock=steady)

    def command(self, message):
        value = message.twist
        now = self.get_clock().now().nanoseconds / 1e9
        stamp = message.header.stamp.sec + message.header.stamp.nanosec / 1e9
        numbers = [value.linear.x, value.linear.y, value.linear.z,
                   value.angular.x, value.angular.y, value.angular.z, stamp, now]
        valid = (message.header.frame_id == self.get_namespace().lstrip('/') + '/base_link'
                 and all(math.isfinite(number) for number in numbers)
                 and -.05 <= now - stamp <= .5
                 and all(abs(number) < 1e-9 for number in numbers[1:5]))
        if not valid:
            self.value = (0., 0.)
            self.received = None
            return
        self.value = (max(-.3, min(.3, value.linear.x)), max(-.3, min(.3, value.angular.z)))
        self.received = time.monotonic()

    def poll_states(self):
        for name, client in self.state_clients.items():
            if name in self.pending or not client.service_is_ready():
                continue
            future = client.call_async(GetState.Request())
            self.pending[name] = future
            def result(done, key=name):
                self.pending.pop(key, None)
                try:
                    self.states[key] = (done.result().current_state.id, time.monotonic())
                except Exception:
                    self.states.pop(key, None)
            future.add_done_callback(result)

    def tick(self):
        now = time.monotonic()
        exclusive = all(name in self.states and self.states[name][0] == 2
                        and now - self.states[name][1] <= .75 for name in self.state_clients)
        fresh = self.received is not None and now - self.received <= .25
        vx, wz = self.value if exclusive and fresh else (0., 0.)
        command = Twist()
        command.linear.x, command.angular.z = vx, wz
        self.publisher.publish(command)


def main():
    rclpy.init()
    node = ManualGate()
    node.get_logger().info('MANUAL gate: Nav2 controller/behavior/navigator must be inactive; stale input stops in 0.25 s')
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.publisher.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
