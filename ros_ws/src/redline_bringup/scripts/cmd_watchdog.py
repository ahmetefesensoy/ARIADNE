#!/usr/bin/env python3
"""Bounded commands and loss timeout for the simulated rover only."""
import math
import time
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from geometry_msgs.msg import Twist


def gated(vx,wz,age,*,timeout=.5):
    if not all(math.isfinite(value) for value in (vx,wz,age)) or age<0 or age>timeout:return 0.,0.
    return max(-.4,min(.4,vx)),max(-.5,min(.5,wz))


class Watchdog(Node):
    def __init__(self):
        super().__init__('sim_command_watchdog',namespace='rover_1')
        self.value=(0.,0.);self.received=None
        self.pub=self.create_publisher(Twist,'cmd_vel_sim',10)
        self.sub=self.create_subscription(Twist,'cmd_vel',self.command,10)
        self.timer=self.create_timer(.05,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))

    def command(self,message):
        self.value=(message.linear.x,message.angular.z);self.received=time.monotonic()

    def tick(self):
        age=float('inf') if self.received is None else time.monotonic()-self.received
        vx,wz=gated(*self.value,age)
        command=Twist();command.linear.x=vx;command.angular.z=wz;self.pub.publish(command)


def main():
    rclpy.init();node=Watchdog()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if rclpy.ok():node.pub.publish(Twist())
        node.destroy_node();rclpy.try_shutdown()

if __name__=='__main__':main()
