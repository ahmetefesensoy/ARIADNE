"""Live return field, crew margins, red/yellow lines and tiles (proje.md §7.5–7.6, §8.4).

`walkback_field` is a thin ROS wrapper around :class:`ReturnFieldModel`:

- the Dijkstra return field is recomputed only when cell states change
  (proje.md §7.5 recompute policy); risk-adjusted consumable needs per crew are
  cached with it;
- every tick only subtracts arrays: ``m_j = (R_j − R_rez,j − W_j,ε) / ṙ_j``;
- the displayed line follows ``min(EV1, EV2)`` per cell (§7.6).

SCENARIO inputs come from ``config/eva.yaml`` (habitat request, reserves, start
consumables, tile range). The daylight (FR-12) and SEP (FR-03) terms apply when their
inputs are given (D012, D014).
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np
import yaml

from .cost_human import (
    DETECTED,
    NOT_DETECTED_LIMITED,
    UNOBSERVED,
    CrewMember,
    SuitModel,
    WalkModel,
    metabolic_power,
    prepare_terrain,
    walking_speed,
)
from .fieldtile import Tile, encode_tile
from .grid import Grid
from .params import PROVENANCE_STATUSES
from .polyline import simplify_ring
from .redline import (
    LIM_BATTERY,
    LIM_CO2,
    LIM_NONE,
    LIM_O2,
    LIM_WATER,
    CrewMargin,
    MarginField,
    Rates,
    Resources,
    combine_crew,
    margins,
    region_contours,
)
from .walkback import nearest_in_largest_component, walkable_components, walkback


@dataclass(frozen=True)
class EvaConfig:
    site_id: str
    crew_ids: tuple[str, ...]
    habitat_requested_xy: tuple[float, float]
    reserve: Resources
    start_minutes_above_reserve: float
    terminate_threshold_min: float
    sigma_fallback_percentile: float
    tile_lo_min: float
    tile_hi_min: float
    tile_bit_depth: int
    line_tolerance_m: float
    min_hole_area_m2: float = 0.0
    z_eps: float = 1.645
    sigma_theta: float = 0.2
    # D010: "nearest_in_largest_component" (D008) or "fixed" (a selected, walkable cell).
    habitat_placement: str = "nearest_in_largest_component"
    habitat_selection: str = ""
    # D010: "nominal_minutes" (T2: reserve + minutes of nominal walking) or "design_point"
    # (the suit holds reserve + design_duration_h at design_metabolic_w for every consumable).
    start_basis: str = "nominal_minutes"
    design_duration_h: float = 8.0
    design_metabolic_w: float = 351.7
    # Reserve per consumable = max(`reserve`, reserve_minutes at the design rate).
    reserve_minutes: float = 0.0
    # Display geometry (D010): vertex budget for both line levels together (0 = none); the
    # simplification tolerance doubles up to max_line_tolerance_m until the budget holds.
    # Vertices are rounded to display_quantum_m (a binary fraction is exact in float32 and
    # serialises short in rosbridge JSON).
    max_display_vertices: int = 0
    max_line_tolerance_m: float = 32.0
    display_quantum_m: float = 0.0


_EVA_KEYS = {"provenance_status", "note", "site_id", "crew_ids", "habitat", "reserve", "start", "lines", "tile",
             "sigma_fallback_percentile", "risk", "sources"}
PLACEMENTS = ("nearest_in_largest_component", "fixed")
START_BASES = ("nominal_minutes", "design_point")


def load_eva(path: Path | str) -> EvaConfig:
    """Strict loader for config/eva.yaml (unknown keys are errors)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if data.get("provenance_status") not in PROVENANCE_STATUSES:
        raise ValueError(f"{path}: provenance_status must be one of {PROVENANCE_STATUSES}")
    unknown = set(data) - _EVA_KEYS
    if unknown:
        raise ValueError(f"{path}: unknown keys {sorted(unknown)}")

    def section(name: str, allowed: set[str]) -> dict:
        value = data.get(name) or {}
        if not isinstance(value, dict) or set(value) - allowed:
            raise ValueError(f"{path}: {name} must be a mapping with keys {sorted(allowed)}")
        return value

    habitat = section("habitat", {"requested_xy_m", "placement", "selection"})
    if habitat.get("placement") not in PLACEMENTS:
        raise ValueError(f"{path}: habitat.placement must be one of {PLACEMENTS}")
    reserve = section("reserve", {f.name for f in fields(Resources)} | {"minutes_at_design_rate"})
    start = section("start", {"basis", "minutes_above_reserve", "design_duration_h", "design_metabolic_w"})
    basis = start.get("basis", "nominal_minutes")
    if basis not in START_BASES:
        raise ValueError(f"{path}: start.basis must be one of {START_BASES}")
    lines = section("lines", {"terminate_threshold_min", "simplify_tolerance_m", "min_hole_area_m2",
                              "max_display_vertices", "max_tolerance_m", "quantum_m"})
    tile = section("tile", {"lo_min", "hi_min", "bit_depth"})
    risk = section("risk", {"z_eps", "sigma_theta"})
    xy = habitat.get("requested_xy_m")
    if not (isinstance(xy, list) and len(xy) == 2):
        raise ValueError(f"{path}: habitat.requested_xy_m must be [x, y]")
    crew_ids = data.get("crew_ids")
    if not (isinstance(crew_ids, list) and crew_ids and all(isinstance(c, str) for c in crew_ids)):
        raise ValueError(f"{path}: crew_ids must be a non-empty list of ids")
    config = EvaConfig(
        site_id=str(data["site_id"]),
        crew_ids=tuple(crew_ids),
        habitat_requested_xy=(float(xy[0]), float(xy[1])),
        reserve=Resources(**{k: float(reserve.get(k, 0.0)) for k in (f.name for f in fields(Resources))}),
        start_minutes_above_reserve=float(start.get("minutes_above_reserve", 0.0)),
        terminate_threshold_min=float(lines["terminate_threshold_min"]),
        sigma_fallback_percentile=float(data["sigma_fallback_percentile"]),
        tile_lo_min=float(tile["lo_min"]),
        tile_hi_min=float(tile["hi_min"]),
        tile_bit_depth=int(tile["bit_depth"]),
        line_tolerance_m=float(lines.get("simplify_tolerance_m", 0.0)),
        min_hole_area_m2=float(lines.get("min_hole_area_m2", 0.0)),
        z_eps=float(risk.get("z_eps", 1.645)),
        sigma_theta=float(risk.get("sigma_theta", 0.2)),
        habitat_placement=str(habitat["placement"]),
        habitat_selection=str(habitat.get("selection", "")),
        start_basis=basis,
        design_duration_h=float(start.get("design_duration_h", 8.0)),
        design_metabolic_w=float(start.get("design_metabolic_w", 351.7)),
        reserve_minutes=float(reserve.get("minutes_at_design_rate", 0.0)),
        max_display_vertices=int(lines.get("max_display_vertices", 0)),
        max_line_tolerance_m=float(lines.get("max_tolerance_m", 32.0)),
        display_quantum_m=float(lines.get("quantum_m", 0.0)),
    )
    values = (config.start_minutes_above_reserve, config.terminate_threshold_min, config.line_tolerance_m,
              config.min_hole_area_m2, config.reserve_minutes, config.design_duration_h, config.design_metabolic_w)
    if not all(math.isfinite(v) and v >= 0 for v in values):
        raise ValueError(f"{path}: start minutes, terminate threshold, tolerance and hole area must be >= 0")
    if not 0 <= config.sigma_fallback_percentile <= 100:
        raise ValueError(f"{path}: sigma_fallback_percentile must be in [0, 100]")
    return config


def nominal_rates(member: CrewMember, suit: SuitModel, walk: WalkModel) -> Rates:
    """Flat walking on unobserved ground: the T2 nominal consumption."""
    speed = walk.speed_factor_unobserved * walking_speed(0.0, walk)
    return Rates.from_metabolic_power(metabolic_power(speed, 0.0, walk.eta_default, member, suit, walk), suit)


def design_rates(suit: SuitModel, eva: EvaConfig) -> Rates:
    """Consumption at the suit's design average metabolic rate (D010)."""
    return Rates.from_metabolic_power(eva.design_metabolic_w, suit)


def reserve_resources(suit: SuitModel, eva: EvaConfig) -> Resources:
    """Per consumable: max(fixed reserve, `reserve_minutes` at the design rate) (D010)."""
    rates, fixed, seconds = design_rates(suit, eva), eva.reserve, eva.reserve_minutes * 60.0
    return Resources(
        o2_kg=max(fixed.o2_kg, rates.o2_kg_s * seconds),
        co2_capacity_kg=max(fixed.co2_capacity_kg, rates.co2_kg_s * seconds),
        water_kg=max(fixed.water_kg, rates.water_kg_s * seconds),
        battery_wh=max(fixed.battery_wh, rates.battery_w * seconds / 3600.0),
    )


def start_resources(member: CrewMember, suit: SuitModel, walk: WalkModel, eva: EvaConfig) -> Resources:
    """SCENARIO EVA start state.

    ``design_point``: reserve + `design_duration_h` at the design metabolic rate (the suit is
    sized for its design point; the crew's real consumption sets the endurance).
    ``nominal_minutes``: reserve + `minutes_above_reserve` of the crew's nominal walking (T2).
    """
    reserve = reserve_resources(suit, eva)
    if eva.start_basis == "design_point":
        rates, seconds = design_rates(suit, eva), eva.design_duration_h * 3600.0
    else:
        rates, seconds = nominal_rates(member, suit, walk), eva.start_minutes_above_reserve * 60.0
    return Resources(
        o2_kg=reserve.o2_kg + rates.o2_kg_s * seconds,
        co2_capacity_kg=reserve.co2_capacity_kg + rates.co2_kg_s * seconds,
        water_kg=reserve.water_kg + rates.water_kg_s * seconds,
        battery_wh=reserve.battery_wh + rates.battery_w * seconds / 3600.0,
    )


@dataclass(frozen=True)
class CrewInput:
    remaining: Resources
    rates: Rates
    xy: tuple[float, float] | None
    o2_need_factor: float = 1.0  # D015: a suit leak also multiplies the O₂ needed to walk back


def leak_factor(o2_rate_kg_s: float, metabolic_w: float, suit: SuitModel) -> float:
    """Reported O₂ rate over the rate the metabolic model expects, never below 1 (D015).

    A leak (spec §8.2: O₂ × k_leak) shows up in Consumables as an O₂ rate above
    the metabolic one; the same factor applies to the O₂ of the walk back.
    """
    expected = Rates.from_metabolic_power(metabolic_w, suit).o2_kg_s
    if not (math.isfinite(o2_rate_kg_s) and math.isfinite(expected) and o2_rate_kg_s > 0 and expected > 0):
        raise ValueError("leak factor needs a positive finite O2 rate and metabolic power")
    return max(1.0, o2_rate_kg_s / expected)


@dataclass(frozen=True, eq=False)
class CrewResult:
    crew_id: str
    margin: MarginField
    now_min: float  # NaN: no position, outside the grid or unreachable cell
    now_limiting: int
    cell: tuple[int, int] | None


@dataclass(frozen=True, eq=False)
class Snapshot:
    field_version: int
    crews: dict[str, CrewResult]
    combined: CrewMargin
    abort_rings: list[np.ndarray]  # (N, 3) map-frame x, y, z; outer CCW, holes CW
    terminate_rings: list[np.ndarray]
    limiting_crew_id: str
    limiting_consumable: int
    margin_now_min: float
    line_tolerance_m: float = 0.0  # simplification actually used for the display rings


@dataclass(frozen=True)
class HabitatPlacement:
    cell: tuple[int, int]
    xy: tuple[float, float]
    report: dict


def slope_sigma_fallback(grid: Grid, eva: EvaConfig) -> float | None:
    """σ for cells without a slope σ: the configured percentile of the known ones, never 0."""
    sigma = np.asarray(grid.layer("slope_sigma_deg"), dtype=float)
    finite = sigma[np.isfinite(sigma)]
    return (float(np.percentile(finite, eva.sigma_fallback_percentile))
            if finite.size and finite.size < sigma.size else None)


def _terrain_for(grid: Grid, state: np.ndarray, walk: WalkModel, sigma_fallback_deg: float | None,
                 blocked: np.ndarray | None = None):
    layers = dict(grid.layers)
    layers["state"] = state
    if blocked is not None:
        layers["blocked"] = blocked
    view = Grid(grid.origin_xy, grid.resolution_m, grid.width, grid.height, layers)
    return prepare_terrain(view, walk, sigma_fallback_deg=sigma_fallback_deg)


def _place_habitat(grid: Grid, terrain, eva: EvaConfig) -> HabitatPlacement:
    requested = grid.cell_index(*eva.habitat_requested_xy)
    labels = walkable_components(terrain)
    if eva.habitat_placement == "fixed":
        if labels[requested] < 0:
            raise ValueError(f"fixed habitat cell {requested} is not walkable on this grid")
        sizes = np.bincount(labels[labels >= 0])
        cell = requested
        report = {"placement": "fixed", "selection": eva.habitat_selection,
                  "component_cells": int(sizes[labels[requested]]),
                  "in_largest_component": bool(labels[requested] == int(np.argmax(sizes)))}
    else:
        cell, report = nearest_in_largest_component(labels, requested)
    return HabitatPlacement(cell, grid.cell_center(*cell), report)


def place_habitat(grid: Grid, walk: WalkModel, eva: EvaConfig) -> HabitatPlacement:
    """The habitat cell the return field is built on, without building the field.

    :class:`ReturnFieldModel` runs the same steps on the grid's start state, so another node
    (rule_monitor, FR-12) finds the same shelter from the same grid and configuration files.
    """
    state = np.asarray(grid.layer("state")).astype(np.uint8)
    return _place_habitat(grid, _terrain_for(grid, state, walk, slope_sigma_fallback(grid, eva)), eva)


class ReturnFieldModel:
    def __init__(self, grid: Grid, walk: WalkModel, suit: SuitModel, crew: Mapping[str, CrewMember],
                 eva: EvaConfig):
        missing = [c for c in eva.crew_ids if c not in crew]
        if missing:
            raise ValueError(f"crew ids {missing} are not in the crew parameters")
        self.walk, self.suit, self.eva = walk, suit, eva
        self.crew = {c: crew[c] for c in eva.crew_ids}
        self._base = grid
        self._state = np.asarray(grid.layer("state")).astype(np.uint8).copy()
        self._blocked = np.zeros(self._state.shape, dtype=bool)
        self.sigma_fallback_deg = slope_sigma_fallback(grid, eva)
        z = np.asarray(grid.layer("z_m"), dtype=float)
        self._z = z
        self.version = 0
        self.dirty = True
        terrain = self._terrain()
        placement = _place_habitat(grid, terrain, eva)
        self.habitat_cell, self.habitat_xy, self.habitat_report = placement.cell, placement.xy, placement.report
        self.reserve = reserve_resources(suit, eva)
        self.recompute(terrain)

    @property
    def grid(self) -> Grid:
        return self._base

    @property
    def state(self) -> np.ndarray:
        return self._state.copy()

    def _terrain(self):
        return _terrain_for(self._base, self._state, self.walk, self.sigma_fallback_deg, self._blocked)

    def recompute(self, terrain=None) -> None:
        """Dijkstra return field and cached risk-adjusted needs per crew."""
        terrain = terrain if terrain is not None else self._terrain()
        self.terrain = terrain
        self.field = walkback(terrain, [self.habitat_cell])
        self._needs = {}
        for crew_id, member in self.crew.items():
            need = self.field.consumables(member, self.suit, self.walk, risk=True, z=self.eva.z_eps,
                                          sigma_theta=self.eva.sigma_theta)
            self._needs[crew_id] = {LIM_O2: need.o2_kg, LIM_CO2: need.co2_kg, LIM_WATER: need.water_kg,
                                    LIM_BATTERY: need.battery_wh}
        self.version += 1
        self.dirty = False

    def apply_states(self, cells: Iterable[tuple[int, int, int]]) -> int:
        """Set observation states; returns how many cells changed (field marked dirty)."""
        return self.apply_updates((iy, ix, state, False) for iy, ix, state in cells)

    def apply_updates(self, updates: Iterable[tuple[int, int, int, bool]]) -> int:
        """(iy, ix, state, blocked) from cells.delta_updates; blocked cells are banned and stay
        banned (D015). Returns how many cells changed (field marked dirty)."""
        changed = 0
        for iy, ix, state, blocked in updates:
            if state not in (UNOBSERVED, DETECTED, NOT_DETECTED_LIMITED):
                raise ValueError(f"unknown CellState code {state}")
            if not (0 <= iy < self._base.height and 0 <= ix < self._base.width):
                raise ValueError(f"cell {(iy, ix)} is outside the grid")
            cell_changed = False
            if self._state[iy, ix] != state:
                self._state[iy, ix] = state
                cell_changed = True
            if blocked and not self._blocked[iy, ix]:
                self._blocked[iy, ix] = True
                cell_changed = True
            changed += cell_changed
        if changed:
            self.dirty = True
        return changed

    def nominal_rates(self, crew_id: str) -> Rates:
        return nominal_rates(self.crew[crew_id], self.suit, self.walk)

    def start_resources(self, crew_id: str) -> Resources:
        return start_resources(self.crew[crew_id], self.suit, self.walk, self.eva)

    def crew_margin(self, crew_id: str, remaining: Resources, rates: Rates,
                    shelter_max_s: float | None = None, daylight_budget_s: float | None = None,
                    o2_need_factor: float = 1.0) -> MarginField:
        """Margins; with `shelter_max_s` (SEP mode, FR-03) cells whose risk-adjusted walk to the
        shelter exceeds it get −inf and LIM_SHELTER (proje.md §7.6). `o2_need_factor` (leak_factor,
        D015) scales the O₂ of the walk back like the reported O₂ rate."""
        if not (math.isfinite(o2_need_factor) and o2_need_factor >= 1.0):
            raise ValueError("o2_need_factor must be finite and >= 1")
        needs = self._needs[crew_id]
        if o2_need_factor != 1.0:
            needs = {**needs, LIM_O2: needs[LIM_O2] * o2_need_factor}
        reserve = self.reserve
        available = {
            LIM_O2: remaining.o2_kg - reserve.o2_kg,
            LIM_CO2: remaining.co2_capacity_kg - reserve.co2_capacity_kg,
            LIM_WATER: remaining.water_kg - reserve.water_kg,
            LIM_BATTERY: remaining.battery_wh - reserve.battery_wh,
        }
        per_second = {LIM_O2: rates.o2_kg_s, LIM_CO2: rates.co2_kg_s, LIM_WATER: rates.water_kg_s,
                      LIM_BATTERY: rates.battery_w / 3600.0}
        if shelter_max_s is None and daylight_budget_s is None:
            return margins(needs, available, per_second)
        time_eps = self.field.time_eps_s(self.eva.z_eps, self.eva.sigma_theta)
        # Daylight (FR-12, §7.6): m = (t_sunset − T_dusk) − t_now − W_time; SEP: T_sh ≤ T_SEP,max.
        return margins(needs, available, per_second,
                       time_need_s=time_eps if daylight_budget_s is not None else None,
                       daylight_budget_s=daylight_budget_s,
                       shelter_time_s=time_eps if shelter_max_s is not None else None,
                       shelter_max_s=shelter_max_s)

    def cell_of(self, xy: tuple[float, float] | None) -> tuple[int, int] | None:
        if xy is None or not all(math.isfinite(v) for v in xy):
            return None
        try:
            return self._base.cell_index(*xy)
        except ValueError:
            return None

    def _contours(self, margin_s: np.ndarray, level_s: float) -> list[np.ndarray]:
        r = self._base.resolution_m
        # Display only: small holes stay visible in MarginField and the tile.
        min_hole_cells = self.eva.min_hole_area_m2 / (r * r)
        return region_contours(margin_s, self._base.origin_xy, r, level_s, min_hole_cells=min_hole_cells)

    def _display(self, rings: list[np.ndarray], tolerance_m: float) -> list[np.ndarray]:
        out = []
        h, w = self._z.shape
        x0, y0 = self._base.origin_xy
        r = self._base.resolution_m
        q = self.eva.display_quantum_m
        for ring in rings:
            ring = simplify_ring(ring, tolerance_m)
            if len(ring) < 4:
                continue  # collapsed below a closed triangle
            ix = np.clip(np.floor((ring[:, 0] - x0) / r).astype(int), 0, w - 1)
            iy = np.clip(np.floor((ring[:, 1] - y0) / r).astype(int), 0, h - 1)
            ring = np.column_stack([ring, self._z[iy, ix]])
            if q > 0:
                ring = np.round(ring / q) * q
            out.append(ring)
        return out

    def lines(self, margin_s: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray], float]:
        """Display rings for abort (0) and terminate (T_term) under the vertex budget."""
        raw_abort = self._contours(margin_s, 0.0)
        raw_terminate = self._contours(margin_s, self.eva.terminate_threshold_min * 60.0)
        tolerance = self.eva.line_tolerance_m
        while True:
            abort, terminate = self._display(raw_abort, tolerance), self._display(raw_terminate, tolerance)
            total = sum(len(x) for x in abort) + sum(len(x) for x in terminate)
            budget = self.eva.max_display_vertices
            if budget <= 0 or total <= budget or tolerance >= self.eva.max_line_tolerance_m:
                return abort, terminate, tolerance
            tolerance = min(max(tolerance, 0.5) * 2.0, self.eva.max_line_tolerance_m)

    def snapshot(self, inputs: Mapping[str, CrewInput], shelter_max_s: float | None = None,
                 daylight_budget_s: float | None = None) -> Snapshot:
        if self.dirty:
            self.recompute()
        unknown = set(inputs) - set(self.crew)
        if unknown or not inputs:
            raise ValueError(f"snapshot needs inputs for known crew ids, got {sorted(inputs)}")
        crews = {}
        for crew_id, item in inputs.items():
            field = self.crew_margin(crew_id, item.remaining, item.rates, shelter_max_s, daylight_budget_s,
                                     item.o2_need_factor)
            cell = self.cell_of(item.xy)
            now, lim = math.nan, LIM_NONE
            if cell is not None:
                now = float(field.margin_s[cell] / 60.0)
                lim = int(field.limiting[cell])
            crews[crew_id] = CrewResult(crew_id, field, now, lim, cell)
        combined = combine_crew({c: crews[c].margin for c in crews})
        placed = [c for c in crews.values() if c.cell is not None]
        limiting_id, limiting_code, now_min = "", LIM_NONE, math.nan
        if placed:
            worst = min(placed, key=lambda c: -math.inf if math.isnan(c.now_min) else c.now_min)
            limiting_id, limiting_code, now_min = worst.crew_id, worst.now_limiting, worst.now_min
        abort, terminate, tolerance = self.lines(combined.field.margin_s)
        return Snapshot(
            field_version=self.version,
            crews=crews,
            combined=combined,
            abort_rings=abort,
            terminate_rings=terminate,
            limiting_crew_id=limiting_id,
            limiting_consumable=limiting_code,
            margin_now_min=now_min,
            line_tolerance_m=tolerance,
        )

    def tile(self, margin_min: np.ndarray) -> Tile:
        return encode_tile(margin_min, self.eva.tile_lo_min, self.eva.tile_hi_min,
                           bit_depth=self.eva.tile_bit_depth)
