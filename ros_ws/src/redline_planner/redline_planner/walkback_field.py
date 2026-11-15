"""Live return field and red line (proje.md §7.5–7.6, §8.4 `walkback_field`; D009).

Inputs
- ``/crew/<id>/state`` (CrewState, frame ``map``): remaining consumables, current
  consumption rates and position. Until a crew member has a state, the
  SCENARIO EVA start state is used (``assume_start_state``) without a position.
- ``/redline/cells/delta`` (CellDelta): observation states; the Dijkstra field
  is recomputed on the next tick. The delta's site, resolution and origin must
  equal the planning grid exactly (geometry equality, not bbox overlap).

Outputs (reliable, transient-local, depth 1)
- ``/redline/margin/<id>`` MarginField: float minutes in grid order (row 0 =
  south, row-major), NaN unreachable; ROS-internal only.
- ``/redline/redline`` RedLine: display polygons of ``min`` over crew (D009);
  ``margin_now_min`` NaN (rosbridge: null) when no crew position is usable.
- ``/redline/tiles/margin_min`` and ``/redline/tiles/margin_min_<id>``
  FieldTile: north-up PNG for Unreal/web (redline_core.fieldtile).

Logic lives in redline_core.field_model; this node converts messages only.
"""
from __future__ import annotations

import array
import math
import time
from dataclasses import replace

import numpy as np
import rclpy
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_updater import Updater
from geometry_msgs.msg import Point32, Polygon
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.clock import Clock as RclClock
from rclpy.clock import ClockType
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from redline_core.cells import delta_updates
from redline_core.field_model import CrewInput, ReturnFieldModel, leak_factor, load_eva
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid
from redline_core.redline import Rates, Resources
from rosgraph_msgs.msg import Clock

from redline_msgs.action import ReturnToShelter
from redline_msgs.msg import CellDelta, CrewState, DoseRate, FieldTile, MarginField, RedLine

DELTA_TOPIC = "/redline/cells/delta"
REDLINE_TOPIC = "/redline/redline"
TILE_TOPIC = "/redline/tiles/margin_min"
MAP_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
STATE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
EVENT_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)


def margin_topic(crew_id: str) -> str:
    return f"/redline/margin/{crew_id}"


def tile_topic(crew_id: str | None = None) -> str:
    return TILE_TOPIC if crew_id is None else f"{TILE_TOPIC}_{crew_id}"


def crew_input(state: CrewState, suit) -> CrewInput:
    """Remaining, rates and position from a CrewState; ValueError if unusable."""
    if state.header.frame_id != "map":
        raise ValueError(f"crew state frame {state.header.frame_id!r} is not map")
    c = state.consumables
    remaining = Resources(c.o2_kg, c.co2_capacity_kg, c.water_kg, c.battery_wh)
    if not all(math.isfinite(v) for v in (c.o2_kg, c.co2_capacity_kg, c.water_kg, c.battery_wh, c.metabolic_w)):
        raise ValueError("consumables must be finite")
    rates = Rates(o2_kg_s=c.o2_rate_kg_h / 3600.0,
                  co2_kg_s=Rates.from_metabolic_power(c.metabolic_w, suit).co2_kg_s,
                  water_kg_s=c.water_rate_kg_h / 3600.0, battery_w=c.battery_rate_w)
    if not all(math.isfinite(v) and v > 0 for v in (rates.o2_kg_s, rates.co2_kg_s, rates.water_kg_s, rates.battery_w)):
        raise ValueError("consumption rates must be positive and finite")
    p = state.pose.pose.position
    xy = (p.x, p.y) if math.isfinite(p.x) and math.isfinite(p.y) else None
    # D015: a leak shows as an O2 rate above the metabolic one; the walk back needs that much more O2.
    return CrewInput(remaining, rates, xy, leak_factor(rates.o2_kg_s, c.metabolic_w, suit))


def _floats(values: np.ndarray) -> array.array:
    out = array.array("f")
    out.frombytes(np.ascontiguousarray(values, dtype=np.float32).tobytes())
    return out


def _polygon(ring: np.ndarray) -> Polygon:
    return Polygon(points=[Point32(x=float(x), y=float(y), z=float(z) if math.isfinite(z) else 0.0)
                           for x, y, z in ring])


class WalkbackFieldNode(Node):
    def __init__(self, **kwargs):
        super().__init__("walkback_field", **kwargs)
        grid_path = str(self.declare_parameter("planning_grid", "").value)
        crew_file = str(self.declare_parameter("crew_file", "").value)
        suit_file = str(self.declare_parameter("suit_file", "").value)
        eva_file = str(self.declare_parameter("eva_file", "").value)
        rate = float(self.declare_parameter("rate_hz", 1.0).value)
        self.assume_start = bool(self.declare_parameter("assume_start_state", True).value)
        self.crew_tiles = bool(self.declare_parameter("publish_crew_tiles", True).value)
        # FR-03 (config/rules.yaml): during a SEP alarm every cell must be within T_SEP_max of shelter.
        self.sep_shelter_max_s = 60.0 * float(self.declare_parameter("sep_shelter_max_min", 20.0).value)
        self.arrive_radius_m = float(self.declare_parameter("arrive_radius_m", 10.0).value)
        # FR-12 daylight (§7.6): needs the SPICE sun table and the scenario's PET → UTC map.
        sun_table = str(self.declare_parameter("sun_table", "").value)
        scenario_file = str(self.declare_parameter("scenario_file", "").value)
        self.dusk_s = 60.0 * float(self.declare_parameter("dusk_min", 30.0).value)
        self.sun = None
        if sun_table and scenario_file:
            from redline_core.scenario import load_scenario
            from redline_data.spice_env import read_sun_table
            t, _, el, _, _ = read_sun_table(sun_table)
            self.sun = (t, el, load_scenario(scenario_file).replay_mapping())
        self.daylight_budget_s = math.nan
        self.sep_alert = False
        self.pet_s = math.nan
        if not all((grid_path, crew_file, suit_file, eva_file)):
            raise ValueError("planning_grid, crew_file, suit_file and eva_file parameters are required")
        if not rate > 0:
            raise ValueError("rate_hz must be > 0")
        grid, self.grid_meta = load_planning_grid(grid_path)
        self.walk, self.suit = load_models(suit_file)
        self.eva = load_eva(eva_file)
        # D015: the scenario crew list overrides eva.yaml (one source for every node).
        crew_ids = [c for c in self.declare_parameter("crew_ids", [""]).value if c]
        if crew_ids:
            self.eva = replace(self.eva, crew_ids=tuple(crew_ids))
        site = self.grid_meta.get("provenance", {}).get("site_id")
        if site is not None and site != self.eva.site_id:
            raise ValueError(f"planning grid is for site {site!r}, eva config for {self.eva.site_id!r}")
        started = time.perf_counter()
        self.model = ReturnFieldModel(grid, self.walk, self.suit, load_crew(crew_file), self.eva)
        self.timing_ms = {"startup": (time.perf_counter() - started) * 1000.0}
        self.states: dict[str, CrewState] = {}
        self.counts = {"ticks": 0, "deltas": 0, "rejected_deltas": 0, "changed_cells": 0, "rejected_states": 0}

        self._margin_pubs = {c: self.create_publisher(MarginField, margin_topic(c), MAP_QOS) for c in self.eva.crew_ids}
        self._tile_pubs = {None: self.create_publisher(FieldTile, tile_topic(), MAP_QOS)}
        if self.crew_tiles:
            self._tile_pubs.update({c: self.create_publisher(FieldTile, tile_topic(c), MAP_QOS)
                                    for c in self.eva.crew_ids})
        self._redline_pub = self.create_publisher(RedLine, REDLINE_TOPIC, MAP_QOS)
        self.create_subscription(CellDelta, DELTA_TOPIC, self._on_delta, EVENT_QOS)
        self.create_subscription(DoseRate, "/env/dose_rate", self._on_dose, STATE_QOS)
        self.create_subscription(Clock, "/redline/mission/clock", self._on_clock, STATE_QOS)
        self._rts = ActionServer(self, ReturnToShelter, "/redline/return_to_shelter", self._execute_rts,
                                 goal_callback=self._accept_rts, cancel_callback=lambda _: CancelResponse.ACCEPT,
                                 callback_group=ReentrantCallbackGroup())
        for crew_id in self.eva.crew_ids:
            self.create_subscription(CrewState, f"/crew/{crew_id}/state",
                                     lambda m, c=crew_id: self._on_state(c, m), STATE_QOS)
        steady = RclClock(clock_type=ClockType.STEADY_TIME)
        self._timer = self.create_timer(1.0 / rate, self._tick, clock=steady)
        self._diagnostics = Updater(self)
        self._diagnostics.setHardwareID(f"walkback_{self.eva.site_id}")
        self._diagnostics.add("walkback_field", self._diagnose)
        hx, hy = self.model.habitat_xy
        self.get_logger().info(f"habitat (SCENARIO) at ({hx:.1f}, {hy:.1f}) m, cell {self.model.habitat_cell}; "
                               f"startup {self.timing_ms['startup']:.0f} ms")

    def _on_delta(self, delta: CellDelta) -> None:
        grid = self.model.grid
        try:
            if delta.header.frame_id != "map" or delta.site_id != self.eva.site_id:
                raise ValueError(f"delta for frame {delta.header.frame_id!r}, site {delta.site_id!r}")
            if (delta.resolution_m != np.float32(grid.resolution_m) or
                    (delta.origin.x, delta.origin.y) != tuple(float(v) for v in grid.origin_xy)):
                raise ValueError("delta geometry differs from the planning grid")
            # D015: speed_factor 0 means an observed obstacle; never read only the state.
            changed = self.model.apply_updates(delta_updates([(c.iy, c.ix, c.state, c.speed_factor, c.evidence_id)
                                                              for c in delta.cells]))
        except ValueError as error:
            self.counts["rejected_deltas"] += 1
            self.get_logger().warning(f"cell delta rejected: {error}")
            return
        self.counts["deltas"] += 1
        self.counts["changed_cells"] += changed

    def _on_state(self, crew_id: str, state: CrewState) -> None:
        if state.crew_id != crew_id:
            self.counts["rejected_states"] += 1
            return
        self.states[crew_id] = state

    def inputs(self) -> dict[str, CrewInput]:
        out = {}
        for crew_id in self.eva.crew_ids:
            state = self.states.get(crew_id)
            if state is not None:
                try:
                    out[crew_id] = crew_input(state, self.suit)
                    continue
                except ValueError as error:
                    self.counts["rejected_states"] += 1
                    self.get_logger().warning(f"{crew_id} state unusable: {error}", throttle_duration_sec=5.0)
            if self.assume_start:
                out[crew_id] = CrewInput(self.model.start_resources(crew_id), self.model.nominal_rates(crew_id), None)
        return out

    def _tick(self) -> None:
        inputs = self.inputs()
        if not inputs:
            return
        started = time.perf_counter()
        recomputing = self.model.dirty
        daylight = None
        if self.sun is not None and math.isfinite(self.pet_s):
            from redline_core.clocks import MissionTime
            from redline_core.solar import daylight_budget_s
            t, el, mapping = self.sun
            utc = mapping.historical_utc(MissionTime(self.pet_s)).timestamp()
            self.daylight_budget_s = daylight_budget_s(t, el, utc, self.dusk_s)
            # Outside the table (NaN) the term is not applied and diagnostics say so.
            daylight = self.daylight_budget_s if not math.isnan(self.daylight_budget_s) else None
        snapshot = self.model.snapshot(inputs, self.sep_shelter_max_s if self.sep_alert else None, daylight)
        if recomputing:
            self.timing_ms["last_recompute_and_snapshot"] = (time.perf_counter() - started) * 1000.0
        else:
            self.timing_ms["last_snapshot"] = (time.perf_counter() - started) * 1000.0
        stamp = self.get_clock().now().to_msg()
        for crew_id, result in snapshot.crews.items():
            self._margin_pubs[crew_id].publish(self._margin_message(stamp, crew_id, result.margin))
        tiles = {None: self.model.tile(snapshot.combined.field.margin_min)}
        if self.crew_tiles:
            for crew_id, result in snapshot.crews.items():
                # One crew member: the combined field is that member's field.
                tiles[crew_id] = tiles[None] if len(snapshot.crews) == 1 else self.model.tile(result.margin.margin_min)
        for key, tile in tiles.items():
            name = "margin_min" if key is None else f"margin_min_{key}"
            self._tile_pubs[key].publish(self._tile_message(stamp, name, tile))
        self._redline_pub.publish(self._redline_message(stamp, snapshot))
        self.line_tolerance_m = snapshot.line_tolerance_m
        self.line_vertices = sum(len(r) for r in snapshot.abort_rings + snapshot.terminate_rings)
        self.timing_ms["last_tick"] = (time.perf_counter() - started) * 1000.0
        self.counts["ticks"] += 1

    def _geometry(self, message) -> None:
        grid = self.model.grid
        message.site_id = self.eva.site_id
        message.resolution_m = float(grid.resolution_m)
        message.origin.x, message.origin.y = (float(v) for v in grid.origin_xy)
        message.width, message.height = int(grid.width), int(grid.height)

    def _margin_message(self, stamp, crew_id, field) -> MarginField:
        message = MarginField()
        message.header.stamp, message.header.frame_id = stamp, "map"
        self._geometry(message)
        message.crew_id = crew_id
        message.margin_min = _floats(field.margin_min.ravel())
        message.limiting = array.array("B", np.ascontiguousarray(field.limiting, dtype=np.uint8).tobytes())
        message.terminate_threshold_min = float(self.eva.terminate_threshold_min)
        return message

    def _tile_message(self, stamp, name, tile) -> FieldTile:
        message = FieldTile()
        message.header.stamp, message.header.frame_id = stamp, "map"
        self._geometry(message)
        message.name, message.unit = name, "min"
        message.scale, message.offset, message.nodata_byte = tile.scale, tile.offset, tile.nodata_byte
        message.png = array.array("B", tile.png)
        return message

    def _redline_message(self, stamp, snapshot) -> RedLine:
        message = RedLine()
        message.header.stamp, message.header.frame_id = stamp, "map"
        message.site_id = self.eva.site_id
        message.abort_regions = [_polygon(r) for r in snapshot.abort_rings]
        message.terminate_regions = [_polygon(r) for r in snapshot.terminate_rings]
        message.limiting_crew_id = snapshot.limiting_crew_id
        message.limiting_consumable = snapshot.limiting_consumable
        message.margin_now_min = snapshot.margin_now_min
        return message

    # --- SEP mode and ReturnToShelter (D012) -------------------------------------------
    def _on_dose(self, message: DoseRate) -> None:
        if message.alert != self.sep_alert:
            self.get_logger().warning(f"SEP mode {'ON' if message.alert else 'OFF'}: shelter limit "
                                      f"{self.sep_shelter_max_s / 60:.0f} min")
        self.sep_alert = message.alert

    def _on_clock(self, message: Clock) -> None:
        self.pet_s = message.clock.sec + message.clock.nanosec * 1e-9

    def _accept_rts(self, goal) -> GoalResponse:
        crew = list(goal.crew_ids) or list(self.eva.crew_ids)
        if goal.shelter_id != "habitat" or any(c not in self.eva.crew_ids for c in crew):
            self.get_logger().warning(f"ReturnToShelter rejected: shelter {goal.shelter_id!r}, crew {crew}")
            return GoalResponse.REJECT  # pr_1 as shelter arrives with T9
        return GoalResponse.ACCEPT

    def crew_return_status(self, crew_ids):
        """(eta_min, distance_m, all_home) over crew with a known position; None if none known."""
        hx, hy = self.model.habitat_xy
        w_eps = self.model.field.time_eps_s(self.eva.z_eps, self.eva.sigma_theta)
        etas, dists, home = [], [], True
        for crew_id in crew_ids:
            state = self.states.get(crew_id)
            if state is None:
                return None
            p = state.pose.pose.position
            cell = self.model.cell_of((p.x, p.y))
            if math.hypot(p.x - hx, p.y - hy) > self.arrive_radius_m:
                home = False
            etas.append(w_eps[cell] / 60.0 if cell is not None else math.inf)
            dists.append(float(self.model.field.distance_m[cell]) if cell is not None else math.inf)
        return max(etas), max(dists), home

    def _execute_rts(self, handle):
        goal = handle.request
        crew = list(goal.crew_ids) or list(self.eva.crew_ids)
        start_pet = self.pet_s
        feedback = ReturnToShelter.Feedback()
        result = ReturnToShelter.Result()
        while rclpy.ok():
            if handle.is_cancel_requested:
                handle.canceled()
                result.outcome, result.reason = ReturnToShelter.Result.CANCELED, "canceled"
                return result
            status = self.crew_return_status(crew)
            if status is not None:
                eta, distance, home = status
                feedback.eta_min, feedback.distance_m = float(eta), float(distance)
                handle.publish_feedback(feedback)
                if home:
                    handle.succeed()
                    result.outcome, result.reason = ReturnToShelter.Result.SUCCEEDED, "all crew at the habitat"
                    result.actual_time_min = float((self.pet_s - start_pet) / 60.0) \
                        if math.isfinite(start_pet) and math.isfinite(self.pet_s) else math.nan
                    return result
            time.sleep(0.2)
        handle.abort()
        result.outcome, result.reason = ReturnToShelter.Result.FAILED, "node shutting down"
        return result

    def _diagnose(self, status):
        status.summary(DiagnosticStatus.WARN if self.counts["rejected_deltas"] else DiagnosticStatus.OK,
                       f"field version {self.model.version}")
        for key, value in {**self.counts, **{f"{k}_ms": f"{v:.1f}" for k, v in self.timing_ms.items()}}.items():
            status.add(key, str(value))
        status.add("crew_with_state", ",".join(sorted(self.states)) or "none")
        status.add("sep_mode", str(self.sep_alert))
        status.add("daylight_budget_min", f"{self.daylight_budget_s / 60.0:.1f}" if self.sun else "not configured")
        status.add("line_tolerance_m", f"{getattr(self, 'line_tolerance_m', float('nan')):g}")
        status.add("line_vertices", str(getattr(self, "line_vertices", 0)))
        status.add("npz_sha256", self.grid_meta["npz_sha256"])
        return status


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WalkbackFieldNode()
    executor = MultiThreadedExecutor()  # the ReturnToShelter execute loop must not block ticks
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
