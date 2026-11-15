"""Scenario player (proje.md §8.1 `scenario_player`, §16; D012).

Owns the run: the scenario file, its run_id and the start of mission time. sim_clock starts
paused; when the graph is ready (a RedLine has been published and the dose and mission-state
publishers exist) the player sets ``running=true`` on sim_clock, so a scenario's timeline
never runs ahead of the nodes that must react to it. Scheduled events are published as
Alerts on ``/redline/scenario/event`` when PET reaches them. ``/redline/scenario/control``
(ScenarioControl) handles START, PAUSE, RESUME, STOP and LOAD; SEEK needs the robot
placement of §4.3 (Gazebo set_pose, "teleport" tag) and is refused until then.
"""
from __future__ import annotations

import json
import math

import rclpy
from rclpy.clock import Clock as RclClock
from rclpy.clock import ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

from redline_core.scenario import encode_event, load_scenario
from redline_msgs.msg import Alert, RedLine
from redline_msgs.srv import ScenarioControl

EVENT_TOPIC = "/redline/scenario/event"
CONTROL_SERVICE = "/redline/scenario/control"
STATE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
MAP_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
EVENT_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)


class ScenarioPlayerNode(Node):
    def __init__(self, **kwargs):
        super().__init__("scenario_player", **kwargs)
        scenario_file = str(self.declare_parameter("scenario_file", "").value)
        if not scenario_file:
            raise ValueError("scenario_file parameter is required")
        self.scenario = load_scenario(scenario_file)
        self.run_id = str(self.declare_parameter("run_id", "").value) or self.scenario.run_id()
        self.auto_start = bool(self.declare_parameter("auto_start", True).value)
        self.require = list(self.declare_parameter("require_publishers",
                                                   ["/env/dose_rate", "/redline/mission/state"]).value)
        self.clock_client = AsyncParameterClient(self, str(self.declare_parameter("clock_node", "sim_clock").value))
        self.started = False
        self.redline_seen = False
        self.pet_s = math.nan
        self.emitted: set[int] = set()
        self._events = self.create_publisher(Alert, EVENT_TOPIC, EVENT_QOS)
        self.create_subscription(Clock, "/redline/mission/clock", self._on_clock, STATE_QOS)
        self.create_subscription(RedLine, "/redline/redline", lambda _: setattr(self, "redline_seen", True), MAP_QOS)
        self.create_service(ScenarioControl, CONTROL_SERVICE, self._on_control)
        self.create_timer(0.2, self._maybe_start, clock=RclClock(clock_type=ClockType.STEADY_TIME))
        self.get_logger().info(f"scenario {self.scenario.scenario_id} run {self.run_id}; "
                               f"{len(self.scenario.events)} scheduled events")

    def ready(self) -> bool:
        return (self.redline_seen and self.clock_client.services_are_ready()
                and all(self.count_publishers(t) > 0 for t in self.require))

    def _alert(self, code: str, text: str, severity: int = Alert.INFO, params: dict | None = None) -> None:
        alert = Alert()
        alert.header.stamp = self.get_clock().now().to_msg()
        alert.alert_id = f"scn-{self.run_id}-{code.lower()}-{len(self.emitted) + 1:03d}"
        alert.severity, alert.code = severity, code
        alert.text = text if params is None else f"{text} {json.dumps(params, sort_keys=True)}"
        alert.related_ids = [self.run_id]
        self._events.publish(alert)

    def _set_running(self, running: bool) -> None:
        self.clock_client.set_parameters([Parameter("running", value=running)])

    def _maybe_start(self) -> None:
        if self.auto_start and not self.started and self.ready():
            self._start()

    def _start(self) -> None:
        self._set_running(True)
        self.started = True
        self._alert("SCENARIO_START", f"{self.scenario.scenario_id} started (seed {self.scenario.seed})")

    def _on_clock(self, message: Clock) -> None:
        self.pet_s = message.clock.sec + message.clock.nanosec * 1e-9
        for k, event in enumerate(self.scenario.events):
            if k not in self.emitted and self.pet_s >= event.t_min * 60.0:
                self.emitted.add(k)
                # D015: canonical payload so consumers (ev_sim) never parse prose.
                self._alert(event.type, encode_event(event, f"scenario event at PET {event.t_min:g} min"),
                            Alert.WARNING)

    def _on_control(self, request: ScenarioControl.Request, response: ScenarioControl.Response):
        response.run_id = self.run_id
        if request.scenario_id and request.scenario_id != self.scenario.scenario_id:
            response.success, response.message = False, f"loaded scenario is {self.scenario.scenario_id}"
            return response
        command = request.command
        response.success = True
        if command == ScenarioControl.Request.LOAD:
            response.message = f"{self.scenario.scenario_id} loaded"
        elif command == ScenarioControl.Request.START:
            if not self.started:
                self._start()
            response.message = "started"
        elif command in (ScenarioControl.Request.PAUSE, ScenarioControl.Request.STOP):
            self._set_running(False)
            response.message = "paused" if command == ScenarioControl.Request.PAUSE else "stopped"
            if command == ScenarioControl.Request.STOP:
                self._alert("SCENARIO_STOP", f"{self.scenario.scenario_id} stopped at PET {self.pet_s / 60:.2f} min")
        elif command == ScenarioControl.Request.RESUME:
            self._set_running(True)
            response.message = "resumed"
        else:
            response.success = False
            response.message = "SEEK needs robot placement on the planned route (set_pose, teleport tag); not yet"
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ScenarioPlayerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
