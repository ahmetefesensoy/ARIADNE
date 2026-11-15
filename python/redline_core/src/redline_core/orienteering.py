"""EVA station selection and ordering under return-margin validity (proje.md §7.9; D011).

A route is habitat → stations → habitat. It is *valid* when the PET timeline
(:func:`redline_core.pet.build_timeline`) holds at every station (R0 − C_ε − W_ε ≥ R_rez),
every station is reached inside its window and the EVA ends (mean walk back included)
within ``max_duration_s``. Its value is the joint expected information gain of its
stations (:mod:`redline_core.science_value`).

Three routes (§7.9):

- ``SCIENCE``: maximum value (then shorter);
- ``SAFE``: maximum tightest departure margin, with value ≥ floor (then more value);
- ``FAST``: shortest EVA, with value ≥ floor (then more value);

floor = ``value_floor_fraction`` × the SCIENCE value. The heuristic is greedy insertion by
value per added time followed by local search (insert, remove, swap in/out, relocate,
2-opt). :meth:`RoutePlanner.exact` enumerates every subset with its Held–Karp minimum-time
order (windows and margins are checked on that order) for up to ``EXACT_MAX`` candidates,
so the heuristic's optimality gap can be reported.

Leg costs come from one forward Dijkstra per start on the planning grid; the walk back is
the return field itself. The planner then works on a compact field holding only the
habitat and candidate cells, so a route evaluation costs microseconds, not a grid pass.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field as dc_field

import numpy as np

from .cost_human import CrewMember, PreparedTerrain, SuitModel, WalkModel
from .pet import PlanStation, Timeline, build_timeline
from .redline import Resources
from .science_value import ScienceModel, joint_eig_bits
from .walkback import LegCost, WalkbackField, leg_costs_from

OBJECTIVES = ("SCIENCE", "SAFE", "FAST")
EXACT_MAX = 12


@dataclass(frozen=True)
class Candidate:
    target_id: str
    cell: tuple[int, int]
    science_class: str
    service_s: float
    tasks: tuple[str, ...] = ()
    window_open_s: float = 0.0
    window_close_s: float = math.inf


@dataclass(frozen=True, eq=False)
class RouteEval:
    order: tuple[int, ...]
    valid: bool
    value_bits: float
    duration_s: float
    min_margin_s: float
    timeline: Timeline | None = dc_field(default=None, repr=False)


class RoutePlanner:
    def __init__(self, terrain: PreparedTerrain, field: WalkbackField, habitat_cell: tuple[int, int],
                 candidates: Sequence[Candidate], science: ScienceModel, prior: np.ndarray,
                 crew: CrewMember, suit: SuitModel, walk: WalkModel, initial: Resources, reserve: Resources,
                 max_duration_s: float, *, z: float = 1.645, sigma_theta: float = 0.2,
                 value_floor_fraction: float = 0.7):
        if not candidates:
            raise ValueError("at least one candidate station is required")
        for c in candidates:
            if c.science_class not in science.p_seen:
                raise ValueError(f"candidate {c.target_id}: no observation model for class {c.science_class!r}")
        self.candidates = tuple(candidates)
        self.science, self.prior = science, np.asarray(prior, dtype=float)
        self.crew, self.suit, self.walk = crew, suit, walk
        self.initial, self.reserve = initial, reserve
        self.max_duration_s, self.z, self.sigma_theta = max_duration_s, z, sigma_theta
        self.value_floor_fraction = value_floor_fraction
        cells = [tuple(habitat_cell)] + [tuple(c.cell) for c in candidates]
        n = len(cells)
        # Compact return field: index k ↔ cell (0, k).
        pick = lambda a: np.array([[a[c] for c in cells]], dtype=float)  # noqa: E731
        self.field = WalkbackField(pick(field.time_s), pick(field.var_s2), pick(field.energy_per_kg_j),
                                   pick(field.distance_m), np.full((1, n), -1, dtype=np.int64))
        self.legs: dict[tuple[int, int], LegCost | None] = {}
        for i, start in enumerate(cells):
            costs = leg_costs_from(terrain, start, cells)
            for j, cost in enumerate(costs):
                if i != j:
                    self.legs[(i, j)] = cost
        self._cache: dict[tuple[int, ...], RouteEval] = {}
        self._eig_cache: dict[tuple[str, ...], float] = {}
        self._orders: dict[int, tuple[int, ...]] | None = None

    # --- evaluation -------------------------------------------------------------------
    def _cost(self, a: tuple[int, int], b: tuple[int, int]) -> LegCost | None:
        return self.legs.get((a[1], b[1]))

    def value(self, order: Sequence[int]) -> float:
        key = tuple(sorted(self.candidates[i].science_class for i in order))
        if key not in self._eig_cache:
            self._eig_cache[key] = joint_eig_bits(self.science, self.prior, key)
        return self._eig_cache[key]

    def evaluate(self, order: Sequence[int]) -> RouteEval:
        order = tuple(order)
        if order in self._cache:
            return self._cache[order]
        stations = [PlanStation(self.candidates[i].target_id, (0, i + 1), self.candidates[i].service_s,
                                self.candidates[i].tasks, self.candidates[i].window_open_s,
                                self.candidates[i].window_close_s) for i in order]
        timeline = build_timeline("HAB", (0, 0), stations, self._cost, self.field, self.crew, self.suit,
                                  self.walk, self.initial, self.reserve, z=self.z, sigma_theta=self.sigma_theta)
        duration = timeline.end_pet_s if order else 0.0
        valid = timeline.valid and math.isfinite(duration) and duration <= self.max_duration_s
        result = RouteEval(order, valid, self.value(order), duration, timeline.min_departure_margin_s, timeline)
        self._cache[order] = result
        return result

    def _score(self, ev: RouteEval, objective: str, floor: float):
        """Comparable score (higher is better) or None when the route is not acceptable."""
        if not ev.valid:
            return None
        if objective == "SCIENCE":
            return (ev.value_bits, -ev.duration_s)
        if ev.value_bits + 1e-12 < floor:
            return None
        if objective == "SAFE":
            return (ev.min_margin_s, ev.value_bits)
        if objective == "FAST":
            return (-ev.duration_s, ev.value_bits)
        raise ValueError(f"objective must be one of {OBJECTIVES}")

    # --- heuristic --------------------------------------------------------------------
    def _greedy(self) -> tuple[int, ...]:
        route: tuple[int, ...] = ()
        while True:
            base = self.evaluate(route)
            best, best_ratio = None, 0.0
            for c in set(range(len(self.candidates))) - set(route):
                for pos in range(len(route) + 1):
                    trial = route[:pos] + (c,) + route[pos:]
                    ev = self.evaluate(trial)
                    if not ev.valid:
                        continue
                    gain = ev.value_bits - base.value_bits
                    added = max(ev.duration_s - base.duration_s, 1.0)
                    if gain > 1e-12 and gain / added > best_ratio:
                        best, best_ratio = trial, gain / added
            if best is None:
                return route
            route = best

    def _neighbours(self, route: tuple[int, ...]):
        unused = set(range(len(self.candidates))) - set(route)
        n = len(route)
        for c in unused:  # insert
            for pos in range(n + 1):
                yield route[:pos] + (c,) + route[pos:]
        for i in range(n):  # remove
            yield route[:i] + route[i + 1:]
        for i in range(n):  # swap a used station for an unused one, re-inserted anywhere
            rest = route[:i] + route[i + 1:]
            for c in unused:
                for pos in range(n):
                    yield rest[:pos] + (c,) + rest[pos:]
        for i in range(n):  # relocate
            rest = route[:i] + route[i + 1:]
            for pos in range(n):
                if pos != i:
                    yield rest[:pos] + (route[i],) + rest[pos:]
        for i in range(n - 1):  # 2-opt reversal
            for j in range(i + 2, n + 1):
                yield route[:i] + route[i:j][::-1] + route[j:]

    def heuristic(self, objective: str, floor: float = 0.0) -> RouteEval:
        route = self._greedy()
        current = self.evaluate(route)
        score = self._score(current, objective, floor)
        improved = True
        while improved:
            improved = False
            for trial in self._neighbours(route):
                ev = self.evaluate(trial)
                s = self._score(ev, objective, floor)
                if s is not None and (score is None or s > score):
                    route, current, score, improved = trial, ev, s, True
                    break
        return current if score is not None else self.evaluate(())

    # --- exact (small instances) --------------------------------------------------------
    def _min_time_orders(self) -> dict[int, tuple[int, ...]]:
        """Minimum walking-time order (habitat → subset → habitat) for every subset mask.

        One Held–Karp table over all candidates (2^n · n states) serves every subset:
        the best order of a mask ends at the last stop minimising path time + walk back.
        Service time is the same for any order of a subset, so it does not enter.
        """
        if self._orders is not None:
            return self._orders
        n = len(self.candidates)
        legs = np.full((n + 1, n + 1), np.inf)
        for (a, b), cost in self.legs.items():
            if cost is not None:
                legs[a, b] = cost.time_s
        back = self.field.time_s[0]
        size = 1 << n
        best = np.full((size, n), np.inf)
        parent = np.full((size, n), -1, dtype=np.int64)
        for k in range(n):
            best[1 << k, k] = legs[0, k + 1]
        for mask in range(1, size):
            for last in range(n):
                if not (mask >> last) & 1 or not np.isfinite(best[mask, last]):
                    continue
                base = best[mask, last]
                for nxt in range(n):
                    if (mask >> nxt) & 1:
                        continue
                    cand = base + legs[last + 1, nxt + 1]
                    nmask = mask | (1 << nxt)
                    if cand < best[nmask, nxt]:
                        best[nmask, nxt] = cand
                        parent[nmask, nxt] = last
        orders: dict[int, tuple[int, ...]] = {}
        for mask in range(1, size):
            totals = best[mask] + back[1:]
            last = int(np.argmin(totals))
            if not np.isfinite(totals[last]):
                continue
            path, m, k = [], mask, last
            while k >= 0:
                path.append(k)
                prev = int(parent[m, k])
                m &= ~(1 << k)
                k = prev
            orders[mask] = tuple(path[::-1])
        self._orders = orders
        return orders

    def exact(self, objective: str, floor: float = 0.0) -> RouteEval:
        n = len(self.candidates)
        if n > EXACT_MAX:
            raise ValueError(f"exact search is limited to {EXACT_MAX} candidates")
        best, best_score = self.evaluate(()), self._score(self.evaluate(()), objective, floor)
        for order in self._min_time_orders().values():
            ev = self.evaluate(order)
            s = self._score(ev, objective, floor)
            if s is not None and (best_score is None or s > best_score):
                best, best_score = ev, s
        return best

    # --- Pareto set ---------------------------------------------------------------------
    def pareto(self, *, with_exact: bool | None = None) -> dict[str, dict]:
        """SCIENCE/SAFE/FAST routes; with exact references and gaps when n ≤ EXACT_MAX."""
        exact_ok = len(self.candidates) <= EXACT_MAX if with_exact is None else with_exact
        out = {}
        science = self.heuristic("SCIENCE")
        reference = self.exact("SCIENCE") if exact_ok else None
        floor = self.value_floor_fraction * max(science.value_bits, reference.value_bits if reference else 0.0)
        for objective in OBJECTIVES:
            heur = science if objective == "SCIENCE" else self.heuristic(objective, floor)
            ex = (reference if objective == "SCIENCE" else self.exact(objective, floor)) if exact_ok else None
            out[objective] = {"route": heur, "exact": ex, "gap": _gap(objective, heur, ex), "floor_bits": floor}
        return out


def _gap(objective: str, heur: RouteEval, exact: RouteEval | None) -> float | None:
    """Relative shortfall of the heuristic on the primary metric (0 = optimal)."""
    if exact is None or not exact.valid:
        return None
    if not heur.valid:
        return 1.0
    if objective == "SCIENCE":
        primary_h, primary_e = heur.value_bits, exact.value_bits
        return 0.0 if primary_e <= 0 else max(0.0, (primary_e - primary_h) / primary_e)
    if objective == "SAFE":
        primary_h, primary_e = heur.min_margin_s, exact.min_margin_s
        return 0.0 if primary_e <= 0 else max(0.0, (primary_e - primary_h) / primary_e)
    primary_h, primary_e = heur.duration_s, exact.duration_s
    return 0.0 if primary_h <= 0 else max(0.0, (primary_h - primary_e) / primary_h)
