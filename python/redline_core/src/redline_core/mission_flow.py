"""Nominal EVA phase logic (proje.md §8.7; D015), pure and testable; `mission_manager` applies it.

BRIEFING → (PRECURSOR →) TRAVERSE ⇄ STATION_SCIENCE → RETURN → DEBRIEF. Mission time is held
during BRIEFING and PRECURSOR, so the walk schedule starts at the PET of the TRAVERSE transition.
A station starts when the schedule is in its service window and every crew member stands within
``station_radius_m``; it ends with the window. RETURN ends when every crew member is within
``shelter_radius_m`` of the shelter. CONTINGENCY and its RETURN are driven by the contingency
path in `mission_manager`, not here; DEBRIEF is final.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from .plan_follow import PlanSchedule

# MissionState phase codes (frozen §5 contract).
BRIEFING, PRECURSOR, TRAVERSE, STATION_SCIENCE, RETURN, CONTINGENCY, DEBRIEF = range(7)


class NominalFlow:
    def __init__(self, crew_ids: Sequence[str], shelter_xy: tuple[float, float], *, precursor: bool = False,
                 station_radius_m: float = 10.0, shelter_radius_m: float = 10.0):
        self.crew_ids = tuple(crew_ids)
        self.shelter_xy = shelter_xy
        self.precursor = precursor
        self.station_radius_m, self.shelter_radius_m = station_radius_m, shelter_radius_m
        self.schedule: PlanSchedule | None = None
        self._services: dict[int, tuple[float, float]] = {}
        self._station: int | None = None

    def begin(self, schedule: PlanSchedule) -> None:
        """Walk schedule of the active plan (built at the TRAVERSE transition)."""
        self.schedule = schedule
        self._services = {index: (start, end) for activity, index, start, end, _ in schedule.items
                          if activity == "service"}
        self._station = None

    def _all_within(self, crew_xy: Mapping[str, tuple[float, float] | None], xy, radius: float) -> bool:
        for crew_id in self.crew_ids:
            p = crew_xy.get(crew_id)
            if p is None or not all(math.isfinite(v) for v in p) or math.hypot(p[0] - xy[0], p[1] - xy[1]) > radius:
                return False
        return True

    def step(self, phase: int, pet_s: float, crew_xy: Mapping[str, tuple[float, float] | None], *,
             plan_ready: bool = True, precursor_done: bool = False) -> tuple[int, str] | None:
        """The next phase and its DecisionRecord context, or None to stay."""
        if phase == BRIEFING:
            if not plan_ready:
                return None
            return (PRECURSOR, "plan accepted; robot precursor before egress") if self.precursor else \
                (TRAVERSE, "plan accepted; egress")
        if phase == PRECURSOR:
            return (TRAVERSE, "precursor done; egress") if plan_ready and precursor_done else None
        if self.schedule is None:
            return None
        last = len(self._services) - 1
        if phase == TRAVERSE:
            xy, activity, index = self.schedule.at(pet_s)
            if activity == "service" and self._all_within(crew_xy, xy, self.station_radius_m):
                self._station = index
                return STATION_SCIENCE, f"arrived at S{index + 1}"
            if activity == "walk" and index == last + 1:
                return RETURN, "no station left; walking home"
            return None
        if phase == STATION_SCIENCE:
            k = self._station
            if k is None:
                _, activity, k = self.schedule.at(pet_s)
                if activity != "service":
                    return None
                self._station = k
            if pet_s >= self._services[k][1]:
                self._station = None
                return (RETURN, f"S{k + 1} done; last station, walking home") if k == last else \
                    (TRAVERSE, f"S{k + 1} done")
            return None
        if phase == RETURN and self._all_within(crew_xy, self.shelter_xy, self.shelter_radius_m):
            return DEBRIEF, "crew in shelter"
        return None
