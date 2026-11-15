"""RAD dose-rate replay on mission time (proje.md §8.1 `rad_replay`, §6.3, §7.12; D012).

Mission PET from ``/redline/mission/clock`` is mapped to historical UTC with the scenario's
replay map (utc = utc0 + PET − PET0). ``/env/dose_rate`` (DoseRate) carries, per detector,
the latest RAD reading at or before that UTC — stepwise, never interpolated — its 6 h
median background and the 25 % alarm of the scenario's detector (redline_core.sep). It is
published on every mission-clock tick, so the alarm reaches subscribers within one tick of
the PET at which the alarming reading begins. ``historical_utc`` is the reading's own
time; ``header.stamp`` is the publication time. Values are ARCHIVE RAD measurements at the
rover; ``sky_view_factor`` is 1 (open sky) until the horizon cube exists.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rclpy
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_updater import Updater
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

from redline_core.clocks import MissionTime
from redline_core.scenario import load_scenario
from redline_core.sep import evaluate
from redline_data.rad import read_rad_table
from redline_msgs.msg import DoseRate

DOSE_TOPIC = "/env/dose_rate"
CLOCK_TOPIC = "/redline/mission/clock"
STATE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)


class RadReplayNode(Node):
    def __init__(self, **kwargs):
        super().__init__("rad_replay", **kwargs)
        scenario_file = str(self.declare_parameter("scenario_file", "").value)
        env_dir = str(self.declare_parameter("env_dir", "").value)
        if not (scenario_file and env_dir):
            raise ValueError("scenario_file and env_dir parameters are required")
        self.scenario = load_scenario(scenario_file)
        self.mapping = self.scenario.replay_mapping()
        rows = []
        for sol in self.scenario.rad_sols:
            table = Path(env_dir) / f"rad_{sol}.csv"
            for r in read_rad_table(table):
                rows.append((r.utc.timestamp(), r.sol, table.name, r.dose_b_ugy_h, r.dose_e_ugy_h))
        if not rows:
            raise ValueError("the scenario names no RAD sols with readings")
        rows.sort()
        self.times = np.array([r[0] for r in rows])
        self.sols = [r[1] for r in rows]
        self.files = [r[2] for r in rows]
        self.readings = {}
        for name, k in (("B", 3), ("E", 4)):
            keep = [i for i, r in enumerate(rows) if r[k] is not None]
            self.readings[name] = (self.times[keep], np.array([rows[i][k] for i in keep]))
        self.alert = False
        self.alert_pet_s = math.nan
        self.published = 0
        self._publisher = self.create_publisher(DoseRate, DOSE_TOPIC, STATE_QOS)
        self.create_subscription(Clock, CLOCK_TOPIC, self._on_clock, STATE_QOS)
        self._diagnostics = Updater(self)
        self._diagnostics.setHardwareID(f"rad_{self.scenario.scenario_id}")
        self._diagnostics.add("rad_replay", self._diagnose)
        first = datetime.fromtimestamp(self.times[0], timezone.utc).isoformat()
        self.get_logger().info(f"{len(rows)} RAD readings from sols {self.scenario.rad_sols}, first {first}, "
                               f"detector {self.scenario.rad_detector}")

    def _on_clock(self, message: Clock) -> None:
        pet = message.clock.sec + message.clock.nanosec * 1e-9
        if pet < self.scenario.pet0_s:
            return
        utc = self.mapping.historical_utc(MissionTime(pet))
        now = utc.timestamp()
        status = evaluate(self.readings, now, detector=self.scenario.rad_detector)
        out = DoseRate()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = "map"
        b, e = status.by_detector["B"], status.by_detector["E"]
        out.dose_rate_b_ugy_h, out.background_b_ugy_h = b.dose, b.background
        out.dose_rate_e_ugy_h, out.background_e_ugy_h = e.dose, e.background
        out.alert = status.alert
        out.alert_detector = self.scenario.rad_detector
        chosen = status.by_detector[self.scenario.rad_detector]
        if math.isfinite(chosen.time_s):
            i = int(np.searchsorted(self.times, chosen.time_s, side="right") - 1)
            out.source_sol, out.source_file = self.sols[i], self.files[i]
            out.historical_utc.sec = int(chosen.time_s)
        out.sky_view_factor = 1.0
        if status.alert and not self.alert:
            self.alert_pet_s = pet
            self.get_logger().warning(f"SEP alarm ({self.scenario.rad_detector}) at PET {pet / 60:.2f} min, "
                                      f"{utc.isoformat()}: {chosen.dose:.2f} vs background {chosen.background:.2f}")
        self.alert = status.alert
        self._publisher.publish(out)
        self.published += 1

    def _diagnose(self, status):
        level = DiagnosticStatus.WARN if self.alert else DiagnosticStatus.OK
        status.summary(level, "SEP alarm" if self.alert else "nominal")
        status.add("published", str(self.published))
        status.add("alert_pet_s", f"{self.alert_pet_s:.1f}")
        return status


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RadReplayNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
