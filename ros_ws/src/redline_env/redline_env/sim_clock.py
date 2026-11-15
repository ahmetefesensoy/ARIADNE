"""Mission (PET) clock publisher (proje.md §4.3, §8.1; D009).

Publishes ``/redline/mission/clock`` as ``rosgraph_msgs/msg/Clock`` whose value
is PET seconds since EVA start. It runs on the host monotonic clock with a
configurable scale and never reads or drives Gazebo ``/clock``: physics time
and mission time stay separate. ``time_scale`` may be changed at runtime with a
parameter set. Seeking belongs to the T6 scenario player.
"""
from __future__ import annotations

import time

import rclpy
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_updater import Updater
from rcl_interfaces.msg import SetParametersResult
from rclpy.clock import Clock as RclClock
from rclpy.clock import ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

from redline_core.mission_clock import MissionClockRunner, split_seconds

TOPIC = "/redline/mission/clock"
STATE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)


class SimClockNode(Node):
    def __init__(self, **kwargs):
        super().__init__("sim_clock", **kwargs)
        start = float(self.declare_parameter("start_pet_s", 0.0).value)
        scale = float(self.declare_parameter("time_scale", 1.0).value)
        rate = float(self.declare_parameter("rate_hz", 10.0).value)
        # A scenario run starts paused; scenario_player sets running=true when the graph is ready.
        running = bool(self.declare_parameter("running", True).value)
        if not rate > 0:
            raise ValueError("rate_hz must be > 0")
        self._runner = MissionClockRunner(start, scale, time.monotonic(), running=running)
        self._publisher = self.create_publisher(Clock, TOPIC, STATE_QOS)
        self._published = 0
        self.add_on_set_parameters_callback(self._on_parameters)
        steady = RclClock(clock_type=ClockType.STEADY_TIME)
        self._timer = self.create_timer(1.0 / rate, self._tick, clock=steady)
        self._diagnostics = Updater(self)
        self._diagnostics.setHardwareID("redline_mission_clock")
        self._diagnostics.add("mission_clock", self._diagnose)
        self.get_logger().info(f"PET from {start} s at scale {scale}, {rate} Hz on {TOPIC}")

    def pet(self) -> float:
        return self._runner.pet(time.monotonic())

    def _on_parameters(self, parameters):
        for parameter in parameters:
            if parameter.name == "time_scale":
                try:
                    self._runner.set_scale(float(parameter.value), time.monotonic())
                except (TypeError, ValueError) as error:
                    return SetParametersResult(successful=False, reason=str(error))
            elif parameter.name == "running":
                (self._runner.resume if parameter.value else self._runner.pause)(time.monotonic())
            elif parameter.name in ("start_pet_s", "rate_hz"):
                return SetParametersResult(successful=False, reason=f"{parameter.name} is fixed at startup")
        return SetParametersResult(successful=True)

    def _tick(self) -> None:
        sec, nanosec = split_seconds(self.pet())
        message = Clock()
        message.clock.sec = sec
        message.clock.nanosec = nanosec
        self._publisher.publish(message)
        self._published += 1

    def _diagnose(self, status):
        status.summary(DiagnosticStatus.OK, "mission clock running")
        status.add("pet_s", f"{self.pet():.3f}")
        status.add("time_scale", f"{self._runner.scale:g}")
        status.add("running", str(self._runner.running))
        status.add("published", str(self._published))
        return status


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SimClockNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
