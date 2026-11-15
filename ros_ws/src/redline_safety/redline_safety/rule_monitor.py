"""Flight-rule monitor, Python MVP (proje.md §8.5 `rule_monitor`, §12; D012, D014).

Evaluates the rules marked ``evaluated: true`` in config/rules.yaml at 10 Hz on mission
time and publishes ``/safety/violations`` (RuleViolation):

- FR-04: shelter mode within the window after a SEP alarm (/env/dose_rate, /redline/mission/state).
  Compliance is also published once as an INFO record so a run can prove the rule held.
- FR-01: margin_now ≥ 0 (/redline/redline). Not applied to a limiting crew member who is already
  in shelter when the limit is daylight (FR-12's case; every other crew member then has a margin at
  least as large, so is at the habitat too) or when the mission is in DEBRIEF (the EVA is over and
  suit consumables no longer bound anything).
- FR-12: at the dusk limit (sunset − T_dusk) every crew member is within the shelter radius of the
  habitat (/crew/<id>/state). Needs the SPICE sun table, the scenario's PET → UTC map and the
  habitat, found from the same grid and configuration as walkback_field (place_habitat). Without
  them the rule is reported as not configured. A crew member without a position counts as outside.

- FR-05 (D015): every crew pair within ``max_distance_m`` and in terrain line of sight (planning
  DTM, eye height 2 m, hysteresis on the clearance); CAUTION at once, WARNING after ``grace_s``
  (PET), INFO when restored. Not applicable to a single crew member. The line of sight is DERIVED:
  relief below the 4 m grid is not seen.
- SUIT_LEAK (S2, §8.7): per crew member, the reported O₂ rate over the metabolic model's rate
  (field_model.leak_factor, D015) stays ≥ factor_on for hold_s (PET) → RuleViolation + an Alert
  ``SUIT_LEAK`` on /redline/alerts naming the crew member; INFO when it falls below factor_off.
  Needs suit_file. Detection only: the response belongs to mission_manager.

Rule logic lives in redline_core.rules and redline_core.los.
"""
from __future__ import annotations

import math
from itertools import combinations

import numpy as np
import rclpy
import yaml
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_updater import Updater
from rclpy.clock import Clock as RclClock
from rclpy.clock import ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

from redline_core.los import sight_clearance
from redline_core.field_model import leak_factor
from redline_core.rules import Fr01Tracker, Fr04Tracker, Fr05Tracker, Fr12Tracker, LeakTracker
from redline_msgs.msg import Alert, CrewState, DoseRate, MarginField, MissionState, RedLine, RuleViolation

VIOLATION_TOPIC = "/safety/violations"
ALERT_TOPIC = "/redline/alerts"
SHELTER_PHASES = (MissionState.CONTINGENCY, MissionState.RETURN, MissionState.DEBRIEF)
SEVERITY = {"INFO": Alert.INFO, "CAUTION": Alert.CAUTION, "WARNING": Alert.WARNING, "EMERGENCY": Alert.EMERGENCY}
LIMIT_NAMES = {MarginField.LIM_O2: "O2", MarginField.LIM_CO2: "CO2", MarginField.LIM_WATER: "water",
               MarginField.LIM_BATTERY: "battery", MarginField.LIM_DAYLIGHT: "daylight",
               MarginField.LIM_SHELTER: "SEP shelter walk"}
STATE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
MAP_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
EVENT_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)


class RuleMonitorNode(Node):
    def __init__(self, **kwargs):
        super().__init__("rule_monitor", **kwargs)
        rules_file = str(self.declare_parameter("rules_file", "").value)
        if not rules_file:
            raise ValueError("rules_file parameter is required")
        with open(rules_file, encoding="utf-8") as handle:
            self.rules = yaml.safe_load(handle)["rules"]
        fr04 = self.rules["FR-04"]
        self.fr04 = Fr04Tracker(float(fr04["window_s"]))
        self.fr01 = Fr01Tracker()
        self.pet_s = math.nan
        self.alert = False
        self.phase = None
        self.margin_now = math.nan
        self.limiting_crew = ""
        self.limiting = MarginField.LIM_O2
        self.counts = {"violations": 0, "fr04_satisfied": 0, "fr12_satisfied": 0, "rejected_states": 0}
        self._setup_shelter()
        self._pub = self.create_publisher(RuleViolation, VIOLATION_TOPIC, EVENT_QOS)
        self._alert_pub = self.create_publisher(Alert, ALERT_TOPIC, EVENT_QOS)
        self.create_subscription(Clock, "/redline/mission/clock", self._on_clock, STATE_QOS)
        self.create_subscription(DoseRate, "/env/dose_rate", lambda m: setattr(self, "alert", m.alert), STATE_QOS)
        self.create_subscription(MissionState, "/redline/mission/state", lambda m: setattr(self, "phase", m.phase),
                                 MAP_QOS)
        self.create_subscription(RedLine, "/redline/redline", self._on_redline, MAP_QOS)
        for crew_id in self.crew_ids:
            self.create_subscription(CrewState, f"/crew/{crew_id}/state", self._on_crew_state, STATE_QOS)
        self.create_timer(0.1, self._tick, clock=RclClock(clock_type=ClockType.STEADY_TIME))
        self._diagnostics = Updater(self)
        self._diagnostics.setHardwareID("flight_rules")
        self._diagnostics.add("rule_monitor", self._diagnose)

    def _setup_shelter(self) -> None:
        """Habitat and crew for the in-shelter test; sun table and scenario for FR-12."""
        grid_path = str(self.declare_parameter("planning_grid", "").value)
        suit_file = str(self.declare_parameter("suit_file", "").value)
        eva_file = str(self.declare_parameter("eva_file", "").value)
        crew_ids = [c for c in self.declare_parameter("crew_ids", [""]).value if c]
        sun_table = str(self.declare_parameter("sun_table", "").value)
        scenario_file = str(self.declare_parameter("scenario_file", "").value)
        fr12 = self.rules.get("FR-12", {})
        self.shelter_radius_m = float(fr12.get("shelter_radius_m", 10.0))
        self.dusk_s = 60.0 * float(fr12.get("t_dusk_min", 30.0))
        self.habitat_xy = None
        self.suit = None
        self.leak_factors: dict[str, float] = {}
        self._dtm = None  # (z, origin, resolution) for FR-05 line of sight
        self.crew_ids: list[str] = []
        if grid_path and suit_file and eva_file:
            from redline_core.field_model import load_eva, place_habitat
            from redline_core.params import load_models
            from redline_core.planning import load_planning_grid
            grid, _ = load_planning_grid(grid_path)
            eva = load_eva(eva_file)
            walk, self.suit = load_models(suit_file)
            self.habitat_xy = place_habitat(grid, walk, eva).xy
            self._dtm = (np.asarray(grid.layer("z_m"), dtype=float), grid.origin_xy, grid.resolution_m)
            self.crew_ids = crew_ids or list(eva.crew_ids)
        self.positions: dict[str, tuple[float, float]] = {}
        self.daylight_budget_s = math.nan
        self.fr12 = None
        self.fr12_status = "not evaluated in rules file"
        if fr12.get("evaluated"):
            missing = [name for name, v in (("sun_table", sun_table), ("scenario_file", scenario_file),
                                            ("planning_grid/suit_file/eva_file", self.habitat_xy)) if not v]
            if missing:
                self.fr12_status = "not configured: needs " + ", ".join(missing)
                self.get_logger().info(f"FR-12 {self.fr12_status}")
            else:
                from redline_core.scenario import load_scenario
                from redline_data.spice_env import read_sun_table
                t, _, el, _, _ = read_sun_table(sun_table)
                self.sun = (t, el, load_scenario(scenario_file).replay_mapping())
                self.fr12 = Fr12Tracker()
                self.fr12_status = "evaluated"
        fr05 = self.rules.get("FR-05", {})
        self.fr05: dict[tuple[str, str], Fr05Tracker] = {}
        self.fr05_status = "not evaluated in rules file"
        if fr05.get("evaluated"):
            if len(self.crew_ids) < 2:
                self.fr05_status = "not applicable: single crew member"
            elif self._dtm is None:
                self.fr05_status = "not configured: needs planning_grid/suit_file/eva_file"
            else:
                self.fr05_eye_m = float(fr05.get("eye_height_m", 2.0))
                self.fr05 = {pair: Fr05Tracker(float(fr05.get("max_distance_m", 100.0)),
                                               float(fr05.get("grace_s", 60.0)),
                                               float(fr05.get("hysteresis_m", 0.5)),
                                               float(fr05.get("distance_hysteresis_m", 0.0)))
                             for pair in combinations(sorted(self.crew_ids), 2)}
                self.fr05_status = "evaluated"
        leak = self.rules.get("SUIT_LEAK", {})
        self.leak: dict[str, LeakTracker] = {}
        self.leak_status = "not evaluated in rules file"
        if leak.get("evaluated"):
            if self.suit is None or not self.crew_ids:
                self.leak_status = "not configured: needs planning_grid/suit_file/eva_file"
            else:
                self.leak = {c: LeakTracker(float(leak.get("factor_on", 1.5)), float(leak.get("factor_off", 1.2)),
                                            float(leak.get("hold_s", 30.0)))
                             for c in self.crew_ids}
                self.leak_status = "evaluated"

    def _on_clock(self, message: Clock) -> None:
        self.pet_s = message.clock.sec + message.clock.nanosec * 1e-9

    def _on_redline(self, message: RedLine) -> None:
        self.margin_now, self.limiting_crew = message.margin_now_min, message.limiting_crew_id
        self.limiting = message.limiting_consumable

    def _on_crew_state(self, message: CrewState) -> None:
        p = message.pose.pose.position
        if message.header.frame_id != "map" or not (math.isfinite(p.x) and math.isfinite(p.y)):
            self.counts["rejected_states"] += 1
            return
        self.positions[message.crew_id] = (p.x, p.y)
        if self.suit is not None:
            c = message.consumables
            try:
                self.leak_factors[message.crew_id] = leak_factor(c.o2_rate_kg_h / 3600.0, c.metabolic_w, self.suit)
            except ValueError:
                self.leak_factors[message.crew_id] = math.nan  # no usable O2 telemetry in this message

    def inside(self) -> set[str] | None:
        """Crew within the shelter radius of the habitat; None if the habitat is unknown."""
        if self.habitat_xy is None:
            return None
        hx, hy = self.habitat_xy
        return {c for c, (x, y) in self.positions.items()
                if c in self.crew_ids and math.hypot(x - hx, y - hy) <= self.shelter_radius_m}

    def _emit(self, rule_id: str, severity: int, value: float, threshold: float, text: str) -> None:
        out = RuleViolation()
        out.header.stamp = self.get_clock().now().to_msg()
        out.rule_id, out.severity, out.value, out.threshold, out.text = rule_id, severity, value, threshold, text
        self._pub.publish(out)
        if severity > Alert.INFO:
            self.counts["violations"] += 1
            self.get_logger().warning(f"{rule_id}: {text}")

    def _tick(self) -> None:
        if not math.isfinite(self.pet_s):
            return
        event = self.fr04.update(self.pet_s, self.alert, self.phase in SHELTER_PHASES)
        window = self.fr04.window_s
        if event == "violated":
            self._emit("FR-04", SEVERITY[self.rules["FR-04"]["severity"]], self.pet_s - self.fr04.alarm_pet_s, window,
                       f"no shelter mode {window:.0f} s (PET) after the SEP alarm")
        elif event in ("satisfied", "late"):
            self.counts["fr04_satisfied"] += event == "satisfied"
            self._emit("FR-04", Alert.INFO if event == "satisfied" else SEVERITY[self.rules["FR-04"]["severity"]],
                       self.fr04.latency_s, window, f"shelter mode {self.fr04.latency_s:.1f} s (PET) after the alarm"
                       + (" (late)" if event == "late" else ""))
        inside = self.inside()
        sheltered = (inside is not None and self.limiting_crew in inside
                     and (self.limiting == MarginField.LIM_DAYLIGHT or self.phase == MissionState.DEBRIEF))
        fr01 = self.fr01.update(math.inf if sheltered else self.margin_now)
        limit = LIMIT_NAMES.get(self.limiting, str(self.limiting))
        if fr01 == "violated":
            self._emit("FR-01", SEVERITY[self.rules["FR-01"]["severity"]], self.margin_now, 0.0,
                       f"{self.limiting_crew} return margin below zero (limit: {limit}): "
                       "cannot cover the walk back plus reserve")
        elif fr01 == "cleared":
            self._emit("FR-01", Alert.INFO, self.margin_now, 0.0,
                       f"{self.limiting_crew} in shelter" if sheltered else "return margin back above zero")
        if self.fr12 is not None:
            self._tick_fr12(inside)
        if self.fr05:
            self._tick_fr05()
        if self.leak:
            self._tick_leak()

    def _tick_leak(self) -> None:
        severity = SEVERITY[self.rules["SUIT_LEAK"].get("severity", "WARNING")]
        for crew_id, tracker in self.leak.items():
            factor = self.leak_factors.get(crew_id, math.nan)
            event = tracker.update(self.pet_s, factor)
            if event == "detected":
                text = (f"{crew_id} suit leak: O2 rate {factor:.2f}x the metabolic model for "
                        f"{tracker.hold_s:.0f} s (PET)")
                self._emit("SUIT_LEAK", severity, factor, tracker.factor_on, text)
                alert = Alert()
                alert.header.stamp = self.get_clock().now().to_msg()
                alert.alert_id = f"alert-leak-{crew_id}-{int(self.pet_s)}"
                alert.severity, alert.code, alert.text, alert.related_ids = severity, "SUIT_LEAK", text, [crew_id]
                self._alert_pub.publish(alert)
            elif event == "cleared":
                self._emit("SUIT_LEAK", Alert.INFO, factor, tracker.factor_off,
                           f"{crew_id} O2 rate back to {factor:.2f}x the metabolic model")

    def _tick_fr05(self) -> None:
        z, origin, resolution = self._dtm
        for (a, b), tracker in self.fr05.items():
            pa, pb = self.positions.get(a), self.positions.get(b)
            if pa is None or pb is None:
                continue
            distance = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            try:
                clearance = sight_clearance(z, origin, resolution, pa, pb, self.fr05_eye_m, self.fr05_eye_m)
            except ValueError:
                clearance = math.nan
            event = tracker.update(self.pet_s, distance, clearance)
            limit = tracker.max_distance_m
            why = []
            if tracker._far:
                why.append(f"{distance:.0f} m apart (limit {limit:.0f} m)")
            if not tracker._visible:
                why.append(f"no line of sight (clearance {clearance:.1f} m)")
            if event == "caution":
                self._emit("FR-05", Alert.CAUTION, distance, limit, f"{a}-{b}: " + "; ".join(why))
            elif event == "warning":
                self._emit("FR-05", SEVERITY[self.rules["FR-05"]["severity"]], distance, limit,
                           f"{a}-{b}: " + "; ".join(why) + f" for {tracker.grace_s:.0f} s (PET)")
            elif event == "cleared":
                self._emit("FR-05", Alert.INFO, distance, limit, f"{a}-{b}: buddy distance and line of sight restored")

    def _tick_fr12(self, inside: set[str]) -> None:
        from redline_core.clocks import MissionTime
        from redline_core.solar import daylight_budget_s
        t, el, mapping = self.sun
        utc = mapping.historical_utc(MissionTime(self.pet_s)).timestamp()
        self.daylight_budget_s = daylight_budget_s(t, el, utc, self.dusk_s)
        outside = sorted(set(self.crew_ids) - inside)
        event = self.fr12.update(self.daylight_budget_s, outside)
        dusk_min, past_min = self.dusk_s / 60.0, -self.daylight_budget_s / 60.0
        if event == "violated":
            where = ", ".join(c if c in self.positions else f"{c} (no position)" for c in outside)
            self._emit("FR-12", SEVERITY[self.rules["FR-12"]["severity"]], past_min, dusk_min,
                       f"outside the shelter at the dusk limit (sunset − {dusk_min:.0f} min): {where}")
        elif event == "satisfied":
            self.counts["fr12_satisfied"] += 1
            self._emit("FR-12", Alert.INFO, past_min, dusk_min,
                       f"all crew in shelter at the dusk limit (sunset − {dusk_min:.0f} min)")
        elif event == "cleared":
            self._emit("FR-12", Alert.INFO, past_min, dusk_min,
                       "all crew back in shelter" if self.daylight_budget_s <= 0 else "daylight budget open again")

    def _diagnose(self, status):
        status.summary(DiagnosticStatus.WARN if self.counts["violations"] else DiagnosticStatus.OK, "rules evaluated")
        for key, value in self.counts.items():
            status.add(key, str(value))
        status.add("fr12", self.fr12_status)
        status.add("fr05", self.fr05_status)
        status.add("suit_leak", self.leak_status)
        if self.fr12 is not None:
            status.add("daylight_budget_min", f"{self.daylight_budget_s / 60.0:.1f}")
        return status


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RuleMonitorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
