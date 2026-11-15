"""Crew physiology, and SIMULATED crew motion for headless runs (proje.md §8.2; D009, D015).

``motion: pose`` (default) is the T5 "EV1 from Unreal, physiology only" mode:

- input ``/crew/<id>/pose`` (geometry_msgs/PoseStamped, frame ``map``) is the presentation
  pose published by Unreal; the node never moves the crew member;
- consumables start at the SCENARIO EVA start state on the **first pose** (egress) and are
  integrated over **mission/PET seconds** from ``/redline/mission/clock``;
- speed and grade come from a short pose window (receipt time), metabolic power from the §7.2
  model (redline_core.suit_state).
- ``scenario_pose_speed_cap_m_s`` is disabled by default (0). An explicit
  positive demo cap meters faster Unreal motion using a SCENARIO extrapolation
  of the walking formula; this is not validated running physiology. The return
  planner and ``motion: plan`` remain walking-only.

``motion: plan`` walks the crew member along the published ``/redline/plan`` on PET (D015):

- egress and the schedule start when MissionState first reaches TRAVERSE; ``trail_s`` makes a
  second crew member follow the same schedule later (redline_core.plan_follow);
- on CONTINGENCY, or RETURN with an active shelter task (mission_manager leaves CONTINGENCY for
  RETURN as soon as ReturnToShelter is accepted, often before a tick sees it; S2, D019), the crew
  member walks home along the return field's path, timed with the walking model; a RETURN without
  a task is the plan's own last leg; in DEBRIEF at the habitat the suit is off (ingress) and
  consumption stops;
- the node publishes ``/crew/<id>/pose`` itself and refuses while another publisher owns it;
- the motion window runs on PET, so walking speed and consumption share one time base.

In both modes a ``SUIT_LEAK`` scenario event for this crew id multiplies the O₂ rate by
``k_leak`` (spec §8.2, SCENARIO). Output ``/crew/<id>/state`` (CrewState). Heart rate, suit
pressure and ppCO₂ have no model and are NaN (rosbridge sends null).
"""
from __future__ import annotations

import math
import time
from dataclasses import replace

import rclpy
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_updater import Updater
from geometry_msgs.msg import Pose, PoseStamped
from rclpy.clock import Clock as RclClock
from rclpy.clock import ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

from redline_core.field_model import ReturnFieldModel, load_eva, start_resources
from redline_core.params import load_crew, load_models
from redline_core.plan_follow import PlanSchedule, timed_path_from_cells
from redline_core.planning import load_planning_grid
from redline_core.redline import Rates
from redline_core.scenario import parse_event
from redline_core.suit_state import MotionWindow, consumption, deplete
from redline_core.walkback import return_path
from redline_msgs.msg import Alert, CrewState, EVAPlan, MissionState

MISSION_CLOCK_TOPIC = "/redline/mission/clock"
STATE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
# Best effort accepts both reliable (rosbridge) and best-effort pose publishers.
POSE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=5, reliability=ReliabilityPolicy.BEST_EFFORT,
                      durability=DurabilityPolicy.VOLATILE)
MAP_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
EVENT_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
WALKING_PHASES = (MissionState.TRAVERSE, MissionState.STATION_SCIENCE, MissionState.RETURN)


def schedule_from_plan(plan: EVAPlan, start_pet_s: float) -> PlanSchedule:
    route = [(p.pose.position.x, p.pose.position.y) for p in plan.route.poses]
    stations = [((s.position.x, s.position.y), 60.0 * s.service_min) for s in plan.stations]
    return PlanSchedule.from_plan(route, stations, [60.0 * leg.duration_min for leg in plan.legs], start_pet_s)


class EvSimNode(Node):
    def __init__(self, **kwargs):
        super().__init__("ev_sim", **kwargs)
        self.crew_id = str(self.declare_parameter("crew_id", "EV1").value)
        crew_file = str(self.declare_parameter("crew_file", "").value)
        suit_file = str(self.declare_parameter("suit_file", "").value)
        eva_file = str(self.declare_parameter("eva_file", "").value)
        rate = float(self.declare_parameter("rate_hz", 5.0).value)
        window_s = float(self.declare_parameter("motion_window_s", 2.0).value)
        max_step_m = float(self.declare_parameter("max_pose_step_m", 20.0).value)
        self.motion = str(self.declare_parameter("motion", "pose").value)
        self.scenario_pose_speed_cap_m_s = float(
            self.declare_parameter("scenario_pose_speed_cap_m_s", 0.0).value)
        self.trail_s = float(self.declare_parameter("trail_s", 0.0).value)
        # D015: the scenario start PET; NaN = the first PET seen in a walking phase.
        self.egress_pet_s = float(self.declare_parameter("egress_pet_s", float("nan")).value)
        grid_path = str(self.declare_parameter("planning_grid", "").value)
        self.shelter_radius_m = float(self.declare_parameter("shelter_radius_m", 10.0).value)
        if not all((crew_file, suit_file, eva_file)):
            raise ValueError("crew_file, suit_file and eva_file parameters are required")
        if not rate > 0:
            raise ValueError("rate_hz must be > 0")
        if self.motion not in ("pose", "plan"):
            raise ValueError("motion must be 'pose' (Unreal) or 'plan' (SIMULATED walk)")
        if not (math.isfinite(self.scenario_pose_speed_cap_m_s)
                and 0 <= self.scenario_pose_speed_cap_m_s <= 5.0):
            raise ValueError("scenario_pose_speed_cap_m_s must be finite and in [0, 5]")
        if self.motion != "pose" and self.scenario_pose_speed_cap_m_s:
            raise ValueError("SCENARIO sprint metering is available only for motion 'pose'")
        if self.motion == "plan" and not grid_path:
            raise ValueError("motion 'plan' needs the planning_grid for the walk home")
        self.walk, self.suit = load_models(suit_file)
        crew = load_crew(crew_file)
        if self.crew_id not in crew:
            raise ValueError(f"crew id {self.crew_id!r} is not in {crew_file}")
        self.member = crew[self.crew_id]
        eva = load_eva(eva_file)
        self.start = start_resources(self.member, self.suit, self.walk, eva)
        self.window = MotionWindow(window_s, max_step_m,
                                   scenario_speed_cap_m_s=self.scenario_pose_speed_cap_m_s or None)
        if self.scenario_pose_speed_cap_m_s:
            self.get_logger().warning(
                f"SCENARIO observed-motion cap {self.scenario_pose_speed_cap_m_s:g} m/s; "
                "physiology above walking speed is extrapolated, not validated running")

        self.remaining = None  # None until egress
        self._pose = None
        self._pet = None
        self._pet_last = None
        self._rates = None
        self._power = math.nan
        self._scenario_extrapolating = False
        self.k_leak = 1.0
        self.ingress = False
        self.phase = None
        self.tasks: list[str] = []
        self.counts = {"poses": 0, "rejected_poses": 0, "pet_backwards": 0, "published": 0, "pose_conflicts": 0,
                       "leak_events": 0, "scenario_extrapolated_ticks": 0}

        self.create_subscription(Clock, MISSION_CLOCK_TOPIC, self._on_clock, STATE_QOS)
        self.create_subscription(Alert, "/redline/scenario/event", self._on_event, EVENT_QOS)
        pose_topic = f"/crew/{self.crew_id}/pose"
        if self.motion == "pose":
            self.create_subscription(PoseStamped, pose_topic, self._on_pose, POSE_QOS)
        else:
            grid, _ = load_planning_grid(grid_path)
            self.model = ReturnFieldModel(grid, self.walk, self.suit, {self.crew_id: self.member},
                                          replace(eva, crew_ids=(self.crew_id,)))
            self.home_xy = self.model.habitat_xy
            self.plan = None
            self.schedule = None
            self.return_walk = None
            self._xy = self.home_xy
            self._pose_topic = pose_topic
            self._pose_pub = self.create_publisher(PoseStamped, pose_topic, POSE_QOS)
            self.create_subscription(EVAPlan, "/redline/plan", self._on_plan, MAP_QOS)
            self.create_subscription(MissionState, "/redline/mission/state", self._on_phase, MAP_QOS)
        self._publisher = self.create_publisher(CrewState, f"/crew/{self.crew_id}/state", STATE_QOS)
        steady = RclClock(clock_type=ClockType.STEADY_TIME)
        self._timer = self.create_timer(1.0 / rate, self._tick, clock=steady)
        self._diagnostics = Updater(self)
        self._diagnostics.setHardwareID(f"crew_{self.crew_id}")
        self._diagnostics.add("ev_sim", self._diagnose)

    # --- inputs -----------------------------------------------------------------------
    def _on_pose(self, message: PoseStamped) -> None:
        p = message.pose.position
        if message.header.frame_id != "map" or not all(math.isfinite(v) for v in (p.x, p.y, p.z)):
            self.counts["rejected_poses"] += 1
            self.get_logger().warning(f"rejected pose (frame {message.header.frame_id!r}); expected finite map pose",
                                      throttle_duration_sec=5.0)
            return
        self.window.add(time.monotonic(), p.x, p.y, p.z)
        self._pose = message.pose
        self.counts["poses"] += 1
        if self.remaining is None:
            self.remaining = self.start
            self.get_logger().info(f"{self.crew_id} egress at ({p.x:.1f}, {p.y:.1f}) m: consumables start")

    def _on_clock(self, message: Clock) -> None:
        self._pet = message.clock.sec + message.clock.nanosec * 1e-9

    def _on_plan(self, message: EVAPlan) -> None:
        if self.schedule is None:  # replans happen before egress only (D015)
            self.plan = message

    def _on_phase(self, message: MissionState) -> None:
        self.phase = message.phase
        self.tasks = list(message.active_task_ids)

    def _on_event(self, alert: Alert) -> None:
        try:
            event = parse_event(alert.text)
        except ValueError as error:
            self.get_logger().warning(f"unreadable scenario event: {error}", throttle_duration_sec=5.0)
            return
        if event is None or event.type != "SUIT_LEAK" or event.params.get("crew_id") != self.crew_id:
            return
        k = float(event.params.get("k_leak", 1.0))
        if not (math.isfinite(k) and k >= 1.0):
            self.get_logger().warning(f"SUIT_LEAK k_leak {k} ignored (must be >= 1)")
            return
        self.k_leak = k
        self.counts["leak_events"] += 1
        self.get_logger().warning(f"{self.crew_id} suit leak: O2 consumption x{k:g} (SCENARIO)")

    # --- plan mode motion ---------------------------------------------------------------
    def _plan_motion(self) -> bool:
        """Advance the SIMULATED walk to the current PET; False while there is nothing to do."""
        if self.phase is None:
            return False
        if self.schedule is None and self.phase in WALKING_PHASES and self.plan is not None:
            start = self.egress_pet_s if math.isfinite(self.egress_pet_s) else self._pet
            self.schedule = schedule_from_plan(self.plan, start)
            self.remaining = self.start
            self.get_logger().info(f"{self.crew_id} egress at PET {self._pet:.1f} s on {self.plan.plan_id}")
        if self.remaining is None:
            return False
        shelter_return = self.phase == MissionState.CONTINGENCY or (self.phase == MissionState.RETURN and self.tasks)
        if shelter_return and self.return_walk is None:
            cells = return_path(self.model.field, self.model.grid.cell_index(*self._xy))
            if cells is None:
                self.get_logger().error(f"{self.crew_id}: no walk home from {self._xy}", throttle_duration_sec=5.0)
            else:
                self.return_walk = timed_path_from_cells(self.model.terrain, self.model.grid, cells, self._pet)
        if self.return_walk is not None:
            self._xy = self.return_walk.position(self._pet)
        else:
            self._xy = self.schedule.at(self._pet, self.trail_s)[0]
        home = math.hypot(self._xy[0] - self.home_xy[0], self._xy[1] - self.home_xy[1]) <= self.shelter_radius_m
        if self.phase == MissionState.DEBRIEF and home and not self.ingress:
            self.ingress = True
            self.get_logger().info(f"{self.crew_id} ingress at PET {self._pet:.1f} s: suit consumption stops")
        z = float(self.model.grid.layer("z_m")[self.model.grid.cell_index(*self._xy)])
        self.window.add(self._pet, self._xy[0], self._xy[1], z)  # PET time base (D015)
        pose = Pose()
        pose.position.x, pose.position.y, pose.position.z = self._xy[0], self._xy[1], z
        pose.orientation.w = 1.0
        self._pose = pose
        if self.count_publishers(self._pose_topic) > 1:
            self.counts["pose_conflicts"] += 1
            self.get_logger().error(f"another node publishes {self._pose_topic}; not publishing a second pose",
                                    throttle_duration_sec=5.0)
        else:
            out = PoseStamped()
            out.header.stamp = self.get_clock().now().to_msg()
            out.header.frame_id = "map"
            out.pose = pose
            self._pose_pub.publish(out)
        return True

    # --- physiology -----------------------------------------------------------------------
    def _tick(self) -> None:
        if self._pet is None:
            return
        if self.motion == "plan":
            if not self._plan_motion():
                return
        elif self.remaining is None:
            return
        motion = self.window.motion(self.walk)
        self._scenario_extrapolating = bool(self.scenario_pose_speed_cap_m_s
                                            and motion.speed_m_s > self.walk.walk_run_speed_m_s)
        if self._scenario_extrapolating:
            self.counts["scenario_extrapolated_ticks"] += 1
        power, rates = consumption(motion, self.walk.eta_default, self.member, self.suit, self.walk)
        if self.k_leak != 1.0:
            rates = Rates(rates.o2_kg_s * self.k_leak, rates.co2_kg_s, rates.water_kg_s, rates.battery_w)
        if self._pet_last is not None:
            dt = self._pet - self._pet_last
            if dt < 0:
                self.counts["pet_backwards"] += 1  # PET moved back (seek): no consumption is undone
            elif self._rates is not None and not self.ingress:
                self.remaining = deplete(self.remaining, self._rates, dt)  # rates in effect during dt
        self._pet_last = self._pet
        self._rates, self._power = rates, power
        self._publisher.publish(self._state_message())
        self.counts["published"] += 1

    def _state_message(self) -> CrewState:
        message = CrewState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "map"
        message.crew_id = self.crew_id
        message.pose.pose = self._pose
        c = message.consumables
        c.header = message.header
        c.crew_id = self.crew_id
        c.o2_kg = self.remaining.o2_kg
        c.water_kg = self.remaining.water_kg
        c.co2_capacity_kg = self.remaining.co2_capacity_kg
        c.battery_wh = self.remaining.battery_wh
        c.o2_rate_kg_h = self._rates.o2_kg_s * 3600.0
        c.water_rate_kg_h = self._rates.water_kg_s * 3600.0
        c.battery_rate_w = self._rates.battery_w
        c.metabolic_w = self._power
        c.theta = self.member.theta
        message.heart_rate_bpm = math.nan
        message.suit_pressure_kpa = math.nan
        message.ppco2_kpa = math.nan
        message.status = CrewState.OK
        return message

    def _diagnose(self, status):
        if self.remaining is None:
            status.summary(DiagnosticStatus.WARN, "waiting for egress (first pose or TRAVERSE)")
        elif self._pet is None:
            status.summary(DiagnosticStatus.WARN, "no mission clock: consumption paused")
        elif self._scenario_extrapolating:
            status.summary(DiagnosticStatus.WARN, "SCENARIO sprint consumption: walking formula extrapolated")
        else:
            status.summary(DiagnosticStatus.OK, "integrating consumables over PET")
        status.add("motion", self.motion)
        status.add("scenario_pose_speed_cap_m_s", f"{self.scenario_pose_speed_cap_m_s:g}")
        status.add("k_leak", f"{self.k_leak:g}")
        status.add("ingress", str(self.ingress))
        for key, value in self.counts.items():
            status.add(key, str(value))
        status.add("pose_window_resets", str(self.window.resets))
        return status


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EvSimNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
