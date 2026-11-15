"""Assemble an orienteering route into an EVA plan (proje.md §7.8–7.9, §8.4; D011).

Stations carry their *marginal* information gain (route value minus the value without
them), legs come from the PET timeline plus a final walk back to the shelter, and the path
follows the time-optimal cells of every leg. The return leg's margin is the departure
margin of the last station (the tightest point of the walk home).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .cost_human import PreparedTerrain
from .grid import Grid
from .orienteering import RouteEval, RoutePlanner
from .walkback import WalkbackField, leg_path, return_path


@dataclass(frozen=True)
class PlannedStation:
    target_id: str
    cell: tuple[int, int]
    xyz: tuple[float, float, float]
    service_s: float
    tasks: tuple[str, ...]
    marginal_value_bits: float
    window_open_s: float
    window_close_s: float


@dataclass(frozen=True)
class PlannedLeg:
    from_id: str
    to_id: str
    duration_s: float
    sigma_s: float
    o2_kg: float
    water_kg: float
    battery_wh: float
    return_margin_s: float


@dataclass(frozen=True, eq=False)
class AssembledPlan:
    objective: str
    valid: bool
    value_bits: float
    total_duration_s: float
    min_margin_s: float
    stations: tuple[PlannedStation, ...]
    legs: tuple[PlannedLeg, ...]
    path_xyz: np.ndarray  # (N, 3) map frame


def assemble_plan(planner: RoutePlanner, route: RouteEval, objective: str, terrain: PreparedTerrain,
                  field: WalkbackField, grid: Grid, habitat_cell: tuple[int, int]) -> AssembledPlan:
    z = np.asarray(grid.layer("z_m"), dtype=float)

    def xyz(cell):
        x, y = grid.cell_center(*cell)
        return (x, y, float(z[cell]) if math.isfinite(z[cell]) else 0.0)

    stations = []
    for k, i in enumerate(route.order):
        c = planner.candidates[i]
        without = route.order[:k] + route.order[k + 1:]
        stations.append(PlannedStation(c.target_id, tuple(c.cell), xyz(c.cell), c.service_s, tuple(c.tasks),
                                       route.value_bits - planner.value(without), c.window_open_s,
                                       c.window_close_s))
    legs = []
    timeline = route.timeline
    if timeline is not None:
        for leg in timeline.legs:
            legs.append(PlannedLeg(leg.from_id, leg.to_id, leg.duration_s, leg.duration_sigma_s, leg.o2_kg,
                                   leg.water_kg, leg.battery_wh, leg.return_margin_s))
    cells: list[tuple[int, int]] = [tuple(habitat_cell)]
    previous = tuple(habitat_cell)
    for station in stations:
        segment = leg_path(terrain, previous, station.cell)
        if segment is None:
            raise ValueError(f"no walkable path to {station.target_id}")
        cells.extend(segment[1:])
        previous = station.cell
    if stations:
        last = stations[-1]
        home = return_path(field, last.cell)
        if home is None:
            raise ValueError(f"no walk back from {last.target_id}")
        cells.extend(home[1:])
        need = field.consumables(planner.crew, planner.suit, planner.walk, risk=False)
        legs.append(PlannedLeg(last.target_id, "HAB", float(field.time_s[last.cell]),
                               float(math.sqrt(field.var_s2[last.cell])), float(need.o2_kg[last.cell]),
                               float(need.water_kg[last.cell]), float(need.battery_wh[last.cell]),
                               route.min_margin_s if timeline is None else timeline.min_departure_margin_s))
    path = np.array([xyz(c) for c in cells], dtype=float)
    return AssembledPlan(objective, route.valid, route.value_bits, route.duration_s, route.min_margin_s,
                         tuple(stations), tuple(legs), path)
