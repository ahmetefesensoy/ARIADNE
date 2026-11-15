"""Value of a robot observation for the EVA plan (proje.md §7.11; D011, revised by D015).

Candidates are lattice points within ``corridor_m`` of the planned path (outbound legs and
every station's walk back) whose footprint holds UNOBSERVED or NOT_DETECTED_LIMITED cells.
The hazard is an impassable obstacle feature (boulder cluster, scarp; D015) covering the
footprint, with SCENARIO density λ_f: p_block = 1 − exp(−λ_f·A_footprint). Small rocks stay
a detour-time term of the walking model (D010) and are not part of this hypothesis.

The plan metric m is the tightest departure margin of the planned station sequence. Walks are
re-routed inside a local window (``window_m``) between the points where they enter and leave
it; costs outside the window are unchanged. If a walk cannot be completed, the variant
without the stations that became unreachable is used.

- with the observation: open → footprint DETECTED (m_open); blocked → the crew plans the
  detour from the window entry (m_blocked);
- without it (the current plan executed blind): open → m_now; blocked → the crew walks the
  plan, sees the obstacle ``sight_m`` before the footprint and detours from there (m_late).

VOI = (1−p)·(m_open − m_now) + p·(m_blocked − m_late) ≥ 0: per walk, observing open ground
never makes a walk longer and a late detour is never cheaper than a planned one (both are
enforced per walk). Station drops appear in both blocked branches and cancel. The value the
spec formula gave before D015, (1−p)·m_open + p·m_blocked − m_now, is kept as
``legacy_voi_s``. score = VOI / robot_cost_s. Values are SCENARIO estimates.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np

from .cost_human import DETECTED, NOT_DETECTED_LIMITED, UNOBSERVED, edge_cost, prepare_terrain
from .field_model import ReturnFieldModel
from .grid import Grid
from .orienteering import RouteEval, RoutePlanner
from .pet import PlanStation, build_timeline
from .walkback import LegCost, WalkbackField, leg_cost, leg_path, return_path


@dataclass(frozen=True)
class VoiCandidate:
    cell: tuple[int, int]
    xy: tuple[float, float]
    p_open: float
    margin_now_s: float
    margin_open_s: float
    margin_blocked_s: float
    voi_s: float
    robot_cost_s: float
    score: float
    compute_ms: float
    margin_late_s: float = math.nan  # blocked and found only on site (D015)
    legacy_voi_s: float = math.nan  # pre-D015 value, diagnostic only


def planned_cost(values) -> LegCost:
    return LegCost(*map(float, values))


def _gain(better: float, worse: float) -> float:
    """better − worse with equal infinities counted as no gain."""
    return 0.0 if better == worse else better - worse


@dataclass
class _Path:
    key: tuple  # ("leg", i, j) or ("ret", i): compact indices
    cells: list[tuple[int, int]]
    cum: np.ndarray  # (len, 4): time, var, energy, distance from the start of the path


def _cumulative(terrain, cells) -> np.ndarray:
    cum = np.zeros((len(cells), 4))
    for k in range(1, len(cells)):
        a, b = cells[k - 1], cells[k]
        cost = edge_cost(terrain, a, (b[0] - a[0], b[1] - a[1]))
        cum[k] = cum[k - 1] + (cost.time_s, cost.var_s2, cost.energy_per_kg_j, cost.distance_m)
    return cum


class VoiEstimator:
    def __init__(self, model: ReturnFieldModel, planner: RoutePlanner, route: RouteEval, *,
                 corridor_m: float = 50.0, window_m: float = 200.0, lattice_m: float = 12.0,
                 footprint_m: float = 6.0, obstacle_density_per_km2: float = 0.0, sight_m: float = 10.0,
                 robot_xy: tuple[float, float] | None = None, robot_speed_m_s: float = 0.1,
                 inspect_s: float = 600.0):
        if not (math.isfinite(obstacle_density_per_km2) and obstacle_density_per_km2 >= 0):
            raise ValueError("obstacle_density_per_km2 must be finite and >= 0")
        if not (math.isfinite(sight_m) and sight_m >= 0):
            raise ValueError("sight_m must be finite and >= 0")
        self.model, self.planner, self.route = model, planner, route
        self.grid: Grid = model.grid
        self.terrain = model.terrain
        self.window_cells = int(round(window_m / 2 / self.grid.resolution_m))
        self.footprint_m, self.lattice_m, self.corridor_m = footprint_m, lattice_m, corridor_m
        self.obstacle_per_m2 = obstacle_density_per_km2 * 1e-6
        self.sight_cells = int(math.ceil(sight_m / self.grid.resolution_m))
        self.robot_xy = robot_xy or model.habitat_xy
        self.robot_speed, self.inspect_s = robot_speed_m_s, inspect_s
        order = route.order
        self.cells = [model.habitat_cell] + [tuple(planner.candidates[i].cell) for i in order]
        self.paths: list[_Path] = []
        for k in range(len(order)):
            cells = leg_path(self.terrain, self.cells[k], self.cells[k + 1])
            if cells is None:
                raise ValueError("planned leg has no path")
            self.paths.append(_Path(("leg", k, k + 1), cells, _cumulative(self.terrain, cells)))
        for k in range(1, len(self.cells)):
            cells = return_path(model.field, self.cells[k])
            if cells is None:
                raise ValueError("planned station has no walk back")
            self.paths.append(_Path(("ret", k), cells, _cumulative(self.terrain, cells)))
        self.margin_now_s = self._margin({})

    # --- plan margin with overridden walks ------------------------------------------
    def _margin(self, overrides: dict) -> float:
        """Tightest departure margin of the planned sequence; stations whose walks fail drop out."""
        dropped = {k for (kind, *idx), cost in overrides.items() if cost is None
                   for k in ([idx[1]] if kind == "leg" else [idx[0]])}
        kept = [k for k in range(1, len(self.cells)) if k not in dropped]
        if not kept:
            return -math.inf
        sequence = [0] + kept
        # Walk costs along the kept sequence: consecutive planned legs or fresh legs when a
        # station was dropped (fresh legs ignore the outcome: a conservative simplification).
        def walk(a, b):
            if b == a + 1 and ("leg", a, b) in overrides:
                return overrides[("leg", a, b)]
            if b == a + 1:
                c = self.paths[a].cum[-1]
                return LegCost(*c)
            return leg_cost(self.terrain, self.cells[a], self.cells[b])

        n = len(self.cells)
        times = np.zeros((1, n)); var = np.zeros((1, n)); energy = np.zeros((1, n)); dist = np.zeros((1, n))
        for k in range(1, n):
            ret = overrides.get(("ret", k))
            values = (ret.time_s, ret.var_s2, ret.energy_per_kg_j, ret.distance_m) if ret is not None and \
                ("ret", k) in overrides else tuple(self.paths[len(self.cells) - 1 + k - 1].cum[-1])
            times[0, k], var[0, k], energy[0, k], dist[0, k] = values
        field = WalkbackField(times, var, energy, dist, np.full((1, n), -1, dtype=np.int64))
        stations, legs = [], {}
        for a, b in zip(sequence, sequence[1:]):
            cost = walk(a, b)
            if cost is None:
                return -math.inf
            legs[(a, b)] = cost
            c = self.planner.candidates[self.route.order[b - 1]]
            stations.append(PlanStation(c.target_id, (0, b), c.service_s, c.tasks, c.window_open_s, c.window_close_s))
        timeline = build_timeline("HAB", (0, 0), stations, lambda x, y: legs.get((x[1], y[1])), field,
                                  self.planner.crew, self.planner.suit, self.planner.walk, self.planner.initial,
                                  self.planner.reserve, z=self.planner.z, sigma_theta=self.planner.sigma_theta)
        return timeline.min_departure_margin_s

    # --- local re-routing -----------------------------------------------------------
    def _window(self, cell):
        h, w = self.grid.height, self.grid.width
        r = self.window_cells
        return max(cell[0] - r, 0), min(cell[0] + r + 1, h), max(cell[1] - r, 0), min(cell[1] + r + 1, w)

    def _outcome_terrain(self, box, footprint, outcome):
        y0, y1, x0, x1 = box
        layers = {name: np.asarray(layer)[y0:y1, x0:x1].copy() for name, layer in self.grid.layers.items()}
        layers["state"] = self.model.state[y0:y1, x0:x1].copy()
        for (iy, ix) in footprint:
            if outcome == "open":
                layers["state"][iy - y0, ix - x0] = DETECTED
            else:
                layers["slope_deg"][iy - y0, ix - x0] = 90.0  # impassable
        x_origin = self.grid.origin_xy[0] + x0 * self.grid.resolution_m
        y_origin = self.grid.origin_xy[1] + y0 * self.grid.resolution_m
        sub = Grid((x_origin, y_origin), self.grid.resolution_m, x1 - x0, y1 - y0, layers)
        return prepare_terrain(sub, self.model.walk, sigma_fallback_deg=self.model.sigma_fallback_deg)

    def _overrides(self, box, footprint, outcome, floor: dict | None = None) -> dict:
        """Walk costs under an outcome for the walks crossing the window (D015).

        open: footprint DETECTED, never longer than planned. blocked: detour planned from the
        window entry, never shorter than planned; only walks through the footprint change.
        late: walk the plan to ``sight_m`` before the footprint and detour from there, never
        cheaper than the planned detour in ``floor`` (the blocked overrides).
        """
        y0, y1, x0, x1 = box
        on_footprint = set(footprint)
        local = None
        out = {}
        for path in self.paths:
            inside = [k for k, (iy, ix) in enumerate(path.cells) if y0 <= iy < y1 and x0 <= ix < x1]
            if not inside:
                continue
            hits = [k for k in inside if path.cells[k] in on_footprint]
            if outcome != "open" and not hits:
                continue  # the obstacle is not on this walk
            if local is None:
                local = self._outcome_terrain(box, footprint, outcome)
            i_in, i_out = inside[0], inside[-1]
            start = max(i_in, hits[0] - self.sight_cells) if outcome == "late" else i_in
            a = (path.cells[start][0] - y0, path.cells[start][1] - x0)
            b = (path.cells[i_out][0] - y0, path.cells[i_out][1] - x0)
            seg = leg_cost(local, a, b) if a != b else LegCost(0.0, 0.0, 0.0, 0.0)
            planned = path.cum[-1]
            if seg is None:
                out[path.key] = planned_cost(planned) if outcome == "open" else None
                continue
            old = path.cum[i_out] - path.cum[start]
            total = planned - old + np.array([seg.time_s, seg.var_s2, seg.energy_per_kg_j, seg.distance_m])
            if outcome == "open" and total[0] > planned[0]:
                total = planned  # the crew can always walk the planned way
            elif outcome == "blocked" and total[0] < planned[0]:
                total = planned
            cost = planned_cost(total)
            if outcome == "late":
                bound = (floor or {}).get(path.key)
                if bound is None:
                    cost = None  # no planned detour exists, so no late one either
                elif cost.time_s < bound.time_s:
                    cost = bound  # a detour found on site is never cheaper than a planned one
            out[path.key] = cost
        return out

    # --- candidates -----------------------------------------------------------------
    def candidate_cells(self) -> list[tuple[int, int]]:
        r = self.grid.resolution_m
        corridor = np.zeros((self.grid.height, self.grid.width), dtype=bool)
        for path in self.paths:
            for iy, ix in path.cells:
                corridor[iy, ix] = True
        from scipy import ndimage

        near = ndimage.distance_transform_edt(~corridor) * r <= self.corridor_m
        step = max(1, int(round(self.lattice_m / r)))
        lattice = np.zeros_like(near)
        lattice[::step, ::step] = True
        unknown = np.isin(self.model.state, (UNOBSERVED, NOT_DETECTED_LIMITED)) & ~self.terrain.banned_mask
        return [tuple(int(v) for v in c) for c in np.argwhere(near & lattice & unknown)]

    def footprint(self, cell) -> list[tuple[int, int]]:
        r = self.grid.resolution_m
        k = int(math.ceil(self.footprint_m / r))
        out = []
        for dy in range(-k, k + 1):
            for dx in range(-k, k + 1):
                iy, ix = cell[0] + dy, cell[1] + dx
                if (0 <= iy < self.grid.height and 0 <= ix < self.grid.width and math.hypot(dy, dx) * r <= self.footprint_m
                        and not self.terrain.banned_mask[iy, ix]):
                    out.append((iy, ix))
        return out

    def evaluate(self, cell) -> VoiCandidate:
        started = time.perf_counter()
        footprint = self.footprint(cell)
        box = self._window(cell)
        area_m2 = len(footprint) * self.grid.resolution_m ** 2
        p_open = math.exp(-self.obstacle_per_m2 * area_m2)
        p_block = 1.0 - p_open
        m_now = self.margin_now_s
        # The crew can always keep the planned timing, so observed open ground never lowers m.
        m_open = max(self._margin(self._overrides(box, footprint, "open")), m_now)
        if p_block > 0.0:
            blocked = self._overrides(box, footprint, "blocked")
            m_blocked = self._margin(blocked)
            m_late = min(self._margin(self._overrides(box, footprint, "late", floor=blocked)), m_blocked)
        else:
            m_blocked = m_late = m_now
        voi = p_open * _gain(m_open, m_now) + p_block * _gain(m_blocked, m_late)
        legacy = p_open * m_open + p_block * m_blocked - m_now
        xy = self.grid.cell_center(*cell)
        cost = math.hypot(xy[0] - self.robot_xy[0], xy[1] - self.robot_xy[1]) / self.robot_speed + self.inspect_s
        return VoiCandidate(cell, xy, p_open, m_now, m_open, m_blocked, voi, cost,
                            max(voi, 0.0) / cost if math.isfinite(voi) else 0.0,
                            (time.perf_counter() - started) * 1000.0, m_late, legacy)

    def rank(self, k: int = 5) -> list[VoiCandidate]:
        results = [self.evaluate(c) for c in self.candidate_cells()]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]
