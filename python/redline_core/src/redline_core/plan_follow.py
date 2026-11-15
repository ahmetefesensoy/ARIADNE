"""SIMULATED crew motion along an EVA plan on mission time (D015).

Headless S0/S2/S4 runs have no Unreal crew, so `ev_sim` walks each crew member along the
published plan. Motion is kinematic and labelled SIMULATED; it never feeds physics.

- :class:`PlanSchedule` is built from the EVAPlan content: route polyline, stations with service
  time, leg durations. Each leg is walked at a constant pace that takes exactly the planned leg
  duration, so the walk keeps the plan's PET; the pace inside a leg does not follow the slope.
- A trailing crew member is the same schedule ``trail_s`` later.
- On RETURN the walk home follows the return path of the walkback field, timed per edge with
  the walking model (:func:`timed_path_from_cells`).
"""
from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from .cost_human import PreparedTerrain, edge_cost
from .grid import Grid

STATION_TOLERANCE_M = 3.0  # stations are cell centres on a route of cell centres


class TimedPath:
    """Positions along a polyline at given times; clamped before the start and after the end."""

    def __init__(self, xy: np.ndarray, times_s: np.ndarray):
        self.xy = np.asarray(xy, dtype=float)
        self.times_s = np.asarray(times_s, dtype=float)
        if self.xy.ndim != 2 or self.xy.shape[1] != 2 or len(self.xy) != len(self.times_s) or not len(self.xy):
            raise ValueError("a timed path needs N points and N times")
        if np.any(np.diff(self.times_s) < 0):
            raise ValueError("path times must not decrease")

    @property
    def duration_s(self) -> float:
        return float(self.times_s[-1] - self.times_s[0])

    def position(self, t: float) -> tuple[float, float]:
        if t <= self.times_s[0]:
            return float(self.xy[0, 0]), float(self.xy[0, 1])
        if t >= self.times_s[-1]:
            return float(self.xy[-1, 0]), float(self.xy[-1, 1])
        return (float(np.interp(t, self.times_s, self.xy[:, 0])),
                float(np.interp(t, self.times_s, self.xy[:, 1])))


def _uniform(xy: np.ndarray, start_s: float, duration_s: float) -> TimedPath:
    steps = np.hypot(*np.diff(xy, axis=0).T) if len(xy) > 1 else np.zeros(0)
    total = float(steps.sum())
    frac = np.concatenate([[0.0], np.cumsum(steps) / total]) if total > 0 else np.linspace(0.0, 1.0, len(xy))
    return TimedPath(xy, start_s + frac * duration_s)


class PlanSchedule:
    def __init__(self, items: list[tuple[str, int, float, float, object]], home_xy: tuple[float, float]):
        self.items = items  # (activity, index, start, end, TimedPath | xy)
        self.home_xy = home_xy
        self.start_pet_s = items[0][2] if items else math.inf
        self.end_pet_s = items[-1][3] if items else -math.inf

    @classmethod
    def from_plan(cls, route_xy, stations: Sequence[tuple[tuple[float, float], float]],
                  leg_durations_s: Sequence[float], start_pet_s: float) -> "PlanSchedule":
        route = np.asarray(route_xy, dtype=float)
        if len(leg_durations_s) != len(stations) + 1:
            raise ValueError(f"{len(stations)} stations need {len(stations) + 1} legs, got {len(leg_durations_s)}")
        if not all(math.isfinite(d) and d >= 0 for d in leg_durations_s):
            raise ValueError("leg durations must be finite and >= 0")
        cuts, start = [0], 0
        for k, (xy, _) in enumerate(stations):
            near = np.hypot(route[start:, 0] - xy[0], route[start:, 1] - xy[1]) <= STATION_TOLERANCE_M
            if not near.any():
                raise ValueError(f"station {k} at {tuple(xy)} is not on the route after point {start}")
            start += int(np.argmax(near))
            cuts.append(start)
        cuts.append(len(route) - 1)
        items, t = [], float(start_pet_s)
        for k, duration in enumerate(leg_durations_s):
            path = _uniform(route[cuts[k]:cuts[k + 1] + 1], t, float(duration))
            items.append(("walk", k, t, t + duration, path))
            t += duration
            if k < len(stations):
                service = float(stations[k][1])
                items.append(("service", k, t, t + service, tuple(map(float, route[cuts[k + 1]]))))
                t += service
        return cls(items, tuple(map(float, route[0])))

    def at(self, pet_s: float, trail_s: float = 0.0) -> tuple[tuple[float, float], str, int]:
        """(xy, activity, index): activity 'walk' (leg index), 'service' (station index) or 'home'."""
        t = pet_s - trail_s
        if t < self.start_pet_s:
            return self.home_xy, "home", -1
        for activity, index, start, end, what in self.items:
            if start <= t < end:
                xy = what.position(t) if activity == "walk" else what
                return xy, activity, index
        last = self.items[-1][4]
        end_xy = last.position(math.inf) if self.items[-1][0] == "walk" else last
        return end_xy, "home", -1


def timed_path_from_cells(terrain: PreparedTerrain, grid: Grid, cells: Sequence[tuple[int, int]],
                          start_s: float) -> TimedPath:
    """Cell path (e.g. walkback.return_path) timed edge by edge with the walking model."""
    if not cells:
        raise ValueError("an empty cell path cannot be walked")
    times = [float(start_s)]
    for a, b in zip(cells, cells[1:]):
        cost = edge_cost(terrain, tuple(a), (b[0] - a[0], b[1] - a[1]))
        if cost is None:
            raise ValueError(f"edge {a} → {b} is not walkable")
        times.append(times[-1] + cost.time_s)
    return TimedPath(np.array([grid.cell_center(*c) for c in cells]), np.array(times))
