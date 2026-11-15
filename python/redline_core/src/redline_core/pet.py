"""EVA plan timeline, return margins and cuff checklist (proje.md §7.8).

PET values are mission-clock seconds from EVA start (not Gazebo /clock).
Station work is modelled as standing (Pandolf V = 0) plus suit cost; margins at a
station are minutes of that dwell consumption, so the return-decision PET is
arrival PET + arrival margin. Daylight is not part of this timeline yet (needs the
T6 environment); the red line applies it via `redline.margins`.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from .cost_human import (
    CrewMember,
    SuitModel,
    WalkModel,
    consumables_from_energy,
    path_consumables,
    standing_power_w,
    station_power_w,
)
from .redline import (
    LIM_BATTERY,
    LIM_CO2,
    LIM_NONE,
    LIM_O2,
    LIM_WATER,
    Rates,
    Resources,
    margins,
)
from .walkback import LegCost, WalkbackField

__all__ = ["LegCost", "PlanStation", "TimelineLeg", "CuffEntry", "Timeline", "build_timeline"]


@dataclass(frozen=True)
class PlanStation:
    station_id: str
    cell: tuple[int, int]
    service_s: float
    tasks: tuple[str, ...] = ()
    window_open_s: float = 0.0  # PET; an earlier arrival waits standing (D011)
    window_close_s: float = math.inf  # PET; a later arrival makes the plan invalid


@dataclass(frozen=True)
class TimelineLeg:
    from_id: str
    to_id: str
    duration_s: float
    duration_sigma_s: float
    o2_kg: float
    co2_kg: float
    water_kg: float
    battery_wh: float
    arrival_pet_s: float
    return_margin_s: float  # at arrival: seconds the crew could keep working before turning back
    limiting: int


@dataclass(frozen=True)
class CuffEntry:
    station_id: str
    arrival_pet_s: float
    tasks: tuple[str, ...]
    return_decision_pet_s: float
    limiting: int


@dataclass(frozen=True)
class Timeline:
    legs: tuple[TimelineLeg, ...]
    cuff: tuple[CuffEntry, ...]
    valid: bool
    first_violation: str | None
    min_departure_margin_s: float = math.inf  # tightest margin when leaving a station (D011)
    end_pet_s: float = math.nan  # last departure + mean walk back to the shelter (D011)
    wait_s: float = 0.0


def build_timeline(
    start_id: str,
    start_cell: tuple[int, int],
    stations: Sequence[PlanStation],
    cost_fn: Callable[[tuple[int, int], tuple[int, int]], LegCost | None],
    field: WalkbackField,
    crew: CrewMember,
    suit: SuitModel,
    model: WalkModel,
    initial: Resources,
    reserve: Resources,
    *,
    z: float = 1.645,
    sigma_theta: float = 0.2,
) -> Timeline:
    """Plan is valid iff R0 - C_ε(s) - W_ε(x(s)) >= R_rez after service at every station."""
    dwell = Rates.from_metabolic_power(station_power_w(crew, suit, model), suit)
    task_w = station_power_w(crew, suit, model) - crew.theta * standing_power_w(crew, model)
    rates = {
        LIM_O2: dwell.o2_kg_s,
        LIM_CO2: dwell.co2_kg_s,
        LIM_WATER: dwell.water_kg_s,
        LIM_BATTERY: dwell.battery_w / 3600.0,
    }
    need_field = field.consumables(crew, suit, model, risk=True, z=z, sigma_theta=sigma_theta)
    headroom = {
        LIM_O2: initial.o2_kg - reserve.o2_kg,
        LIM_CO2: initial.co2_capacity_kg - reserve.co2_capacity_kg,
        LIM_WATER: initial.water_kg - reserve.water_kg,
        LIM_BATTERY: initial.battery_wh - reserve.battery_wh,
    }

    def station_margin(elapsed_s, var_s2, energy_per_kg_j, distance_m, service_s, cell):
        # Standing and the battery base load run for the whole elapsed time; the task increment
        # applies only during station service (D010).
        walk = path_consumables(elapsed_s, energy_per_kg_j, distance_m, crew, suit, model)
        task = consumables_from_energy(task_w * service_s, 0.0, suit)
        factor = 1.0 + z * math.sqrt(var_s2 / elapsed_s**2 + sigma_theta**2) if elapsed_s > 0 else 1.0
        scaled = walk.scaled(factor)
        used = type(walk)(scaled.o2_kg + task.o2_kg, scaled.co2_kg + task.co2_kg,
                          scaled.water_kg + task.water_kg, scaled.battery_wh + task.battery_wh)
        needs = {
            LIM_O2: np.array([need_field.o2_kg[cell]]),
            LIM_CO2: np.array([need_field.co2_kg[cell]]),
            LIM_WATER: np.array([need_field.water_kg[cell]]),
            LIM_BATTERY: np.array([need_field.battery_wh[cell]]),
        }
        available = {
            LIM_O2: headroom[LIM_O2] - used.o2_kg,
            LIM_CO2: headroom[LIM_CO2] - used.co2_kg,
            LIM_WATER: headroom[LIM_WATER] - used.water_kg,
            LIM_BATTERY: headroom[LIM_BATTERY] - used.battery_wh,
        }
        result = margins(needs, available, rates)
        return float(result.margin_s[0]), int(result.limiting[0])

    legs, cuff = [], []
    elapsed = var = energy = distance = service = waited = 0.0
    min_departure = math.inf
    valid, first_violation = True, None
    prev_id, prev_cell = start_id, tuple(start_cell)
    for station in stations:
        cell = tuple(station.cell)
        cost = cost_fn(prev_cell, cell)
        if cost is None:
            valid, first_violation = False, first_violation or station.station_id
            break
        elapsed += cost.time_s
        if elapsed > station.window_close_s and valid:
            valid, first_violation = False, station.station_id  # arrives after the window closes
        if elapsed < station.window_open_s:
            waited += station.window_open_s - elapsed  # standing: path_consumables covers it via T
            elapsed = station.window_open_s
        var += cost.var_s2
        energy += cost.energy_per_kg_j
        distance += cost.distance_m
        arrival_margin, limiting = station_margin(elapsed, var, energy, distance, service, cell)
        used = path_consumables(cost.time_s, cost.energy_per_kg_j, cost.distance_m, crew, suit, model)
        legs.append(
            TimelineLeg(prev_id, station.station_id, cost.time_s, math.sqrt(cost.var_s2), used.o2_kg,
                        used.co2_kg, used.water_kg, used.battery_wh, elapsed, arrival_margin, limiting)
        )
        decision = elapsed + arrival_margin if math.isfinite(arrival_margin) else elapsed
        cuff.append(CuffEntry(station.station_id, elapsed, tuple(station.tasks), decision, limiting))
        elapsed += station.service_s
        service += station.service_s
        departure_margin, _ = station_margin(elapsed, var, energy, distance, service, cell)
        min_departure = min(min_departure, departure_margin if limiting != LIM_NONE else -math.inf)
        if valid and not (departure_margin >= 0.0 and limiting != LIM_NONE):
            valid, first_violation = False, station.station_id
        prev_id, prev_cell = station.station_id, cell
    back = field.time_s[prev_cell] if legs or not stations else math.nan
    return Timeline(tuple(legs), tuple(cuff), valid, first_violation, min_departure,
                    float(elapsed + back) if math.isfinite(back) else math.inf, waited)
