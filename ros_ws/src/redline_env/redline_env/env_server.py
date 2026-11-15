"""Environment state on mission time (proje.md §8.1 `env_server`; D014).

``/env/state`` (EnvState, 1 Hz): Sun azimuth/elevation and Mars→Earth light time
interpolated from the SPICE sun table (redline_data.spice_env), LMST from Mars24 at the
site longitude, and the scenario's own mission sol (PET / sol length, counted from 1).
Pressure, temperatures, tau and air density stay NaN until REMS replay exists (rosbridge
sends null). Mission PET maps to historical UTC with the scenario's replay map.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import rclpy
from rclpy.clock import Clock as RclClock
from rclpy.clock import ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

from redline_core.clocks import MissionTime
from redline_core.scenario import load_scenario
from redline_core.solar import SOL_S, format_hours, interpolate, lmst_hours
from redline_data.spice_env import read_sun_table
from redline_msgs.msg import EnvState, Provenance

ENV_TOPIC = "/env/state"
STATE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)


class EnvServerNode(Node):
    def __init__(self, **kwargs):
        super().__init__("env_server", **kwargs)
        table = str(self.declare_parameter("sun_table", "").value)
        scenario = str(self.declare_parameter("scenario_file", "").value)
        if not (table and scenario):
            raise ValueError("sun_table and scenario_file parameters are required")
        self.mapping = load_scenario(scenario).replay_mapping()
        self.t, self.az, self.el, self.lt, self.meta = read_sun_table(table)
        self.lon = float(self.meta["site"]["lon_east_deg"])
        self.table_name = table.rsplit("/", 1)[-1]
        self.pet_s = math.nan
        self._pub = self.create_publisher(EnvState, ENV_TOPIC, STATE_QOS)
        self.create_subscription(Clock, "/redline/mission/clock", self._on_clock, STATE_QOS)
        self.create_timer(1.0, self._publish, clock=RclClock(clock_type=ClockType.STEADY_TIME))

    def _on_clock(self, message: Clock) -> None:
        self.pet_s = message.clock.sec + message.clock.nanosec * 1e-9

    def state(self) -> EnvState | None:
        if not math.isfinite(self.pet_s):
            return None
        utc = self.mapping.historical_utc(MissionTime(self.pet_s))
        now = utc.timestamp()
        out = EnvState()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = "map"
        out.sun_el_deg = interpolate(self.t, self.el, now)
        # Azimuth wraps at 360: interpolate the unit vector, not the angle.
        sin_az = interpolate(self.t, [math.sin(math.radians(a)) for a in self.az], now)
        cos_az = interpolate(self.t, [math.cos(math.radians(a)) for a in self.az], now)
        out.sun_az_deg = math.degrees(math.atan2(sin_az, cos_az)) % 360.0 if math.isfinite(sin_az) else math.nan
        out.lmst = format_hours(lmst_hours(utc, self.lon))
        out.mission_sol = int(self.pet_s // SOL_S) + 1
        out.earth_light_time_s = interpolate(self.t, self.lt, now)
        out.pressure_pa = out.air_temp_k = out.ground_temp_k = out.tau = out.air_density_kg_m3 = math.nan
        out.provenance.status = Provenance.DERIVED
        out.provenance.product_id = self.table_name
        out.provenance.sha256 = self.meta["csv_sha256"]
        out.provenance.note = "SPICE sun table (geometric horizon); REMS fields not replayed yet"
        return out

    def _publish(self) -> None:
        message = self.state()
        if message is not None:
            self._pub.publish(message)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EnvServerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
