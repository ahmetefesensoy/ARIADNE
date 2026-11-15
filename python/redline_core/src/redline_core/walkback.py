"""Return field: multi-source Dijkstra on the reversed walking graph (proje.md §7.5).

The scalar key is walking time. Variance and walking energy per kg are carried
along the time-optimal path, so consumables for any crew member (θ, W, L) follow
without re-running Dijkstra. Consumables are *affine* in θ (suit power and base
battery load are not scaled), not linear as the spec text says; carrying
(time, energy) keeps the result exact.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numba import njit

from .cost_human import (
    Consumables,
    CrewMember,
    PreparedTerrain,
    SuitModel,
    WalkModel,
    _edge,
    path_consumables,
)


@dataclass(frozen=True)
class LegCost:
    time_s: float
    var_s2: float
    energy_per_kg_j: float
    distance_m: float


@njit(cache=True)
def _push(keys, values, size, key, value):
    if size == keys.size:
        grown_k = np.empty(2 * keys.size)
        grown_v = np.empty(2 * keys.size, dtype=np.int64)
        grown_k[:size] = keys[:size]
        grown_v[:size] = values[:size]
        keys, values = grown_k, grown_v
    i = size
    while i > 0:
        parent = (i - 1) >> 1
        if keys[parent] <= key:
            break
        keys[i] = keys[parent]
        values[i] = values[parent]
        i = parent
    keys[i] = key
    values[i] = value
    return keys, values, size + 1


@njit(cache=True)
def _dijkstra(height, width, sources, reverse, target, z, banned, speed_f, sigma_f, sigma_rad, eta, rock, p,
              offsets, part_n, part_d, part_w, block_n, block_d):
    n = height * width
    dist = np.full(n, np.inf)
    var = np.zeros(n)
    energy = np.zeros(n)
    travel = np.zeros(n)
    hop = np.full(n, -1, dtype=np.int64)
    done = np.zeros(n, dtype=np.bool_)
    keys = np.empty(max(16, n))
    values = np.empty(max(16, n), dtype=np.int64)
    size = 0
    for s in sources:
        if dist[s] > 0.0:
            dist[s] = 0.0
            keys, values, size = _push(keys, values, size, 0.0, s)
    while size > 0:
        key = keys[0]
        u = values[0]
        size -= 1
        if size > 0:
            last_k = keys[size]
            last_v = values[size]
            i = 0
            while True:
                child = 2 * i + 1
                if child >= size:
                    break
                if child + 1 < size and keys[child + 1] < keys[child]:
                    child += 1
                if keys[child] >= last_k:
                    break
                keys[i] = keys[child]
                values[i] = values[child]
                i = child
            keys[i] = last_k
            values[i] = last_v
        if done[u] or key > dist[u]:
            continue
        done[u] = True
        if u == target:
            break
        uy = u // width
        ux = u - uy * width
        for o in range(offsets.shape[0]):
            if reverse:
                vy = uy - offsets[o, 0]
                vx = ux - offsets[o, 1]
            else:
                vy = uy + offsets[o, 0]
                vx = ux + offsets[o, 1]
            if vy < 0 or vy >= height or vx < 0 or vx >= width:
                continue
            v = vy * width + vx
            if done[v]:
                continue
            start = v if reverse else u
            ok, t, sigma, e, d = _edge(start, o, width, z, banned, speed_f, sigma_f, sigma_rad, eta, rock, p,
                                       offsets, part_n, part_d, part_w, block_n, block_d)
            if not ok:
                continue
            candidate = dist[u] + t
            if candidate < dist[v]:
                dist[v] = candidate
                var[v] = var[u] + sigma * sigma
                energy[v] = energy[u] + e
                travel[v] = travel[u] + d
                hop[v] = u
                keys, values, size = _push(keys, values, size, candidate, v)
    return dist, var, energy, travel, hop


@njit(cache=True)
def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


@njit(cache=True)
def _components(height, width, z, banned, speed_f, sigma_f, sigma_rad, eta, rock, p,
                offsets, part_n, part_d, part_w, block_n, block_d):
    n = height * width
    parent = np.arange(n)
    for a in range(n):
        if banned[a]:
            continue
        ay = a // width
        ax = a - ay * width
        for o in range(offsets.shape[0]):
            by = ay + offsets[o, 0]
            bx = ax + offsets[o, 1]
            if by < 0 or by >= height or bx < 0 or bx >= width:
                continue
            ok, _, _, _, _ = _edge(a, o, width, z, banned, speed_f, sigma_f, sigma_rad, eta, rock, p,
                                offsets, part_n, part_d, part_w, block_n, block_d)
            if ok:
                ra = _find(parent, a)
                rb = _find(parent, by * width + bx)
                if ra != rb:
                    parent[rb] = ra
    labels = np.full(n, -1, dtype=np.int64)
    root_label = np.full(n, -1, dtype=np.int64)
    count = 0
    for a in range(n):
        if banned[a]:
            continue
        r = _find(parent, a)
        if root_label[r] < 0:
            root_label[r] = count
            count += 1
        labels[a] = root_label[r]
    return labels


def walkable_components(terrain: PreparedTerrain) -> np.ndarray:
    """Component label per cell under the actual edge rules (walking edges are symmetric);
    -1 for banned cells. Two cells share a label iff one can walk to the other."""
    labels = _components(terrain.height, terrain.width, *terrain.kernel_args())
    return labels.reshape(terrain.height, terrain.width)


def nearest_in_largest_component(labels: np.ndarray, cell: tuple[int, int]) -> tuple[tuple[int, int], dict]:
    """D008 SCENARIO habitat rule: the cell nearest to `cell` inside the largest
    walkable component (ties: lowest flat index). Returns the cell and a report."""
    labels = np.asarray(labels)
    iy, ix = cell
    if not (0 <= iy < labels.shape[0] and 0 <= ix < labels.shape[1]):
        raise ValueError(f"cell {cell} is outside the grid")
    valid = labels[labels >= 0]
    if valid.size == 0:
        raise ValueError("no walkable cell in the grid")
    sizes = np.bincount(valid)
    largest = int(np.argmax(sizes))
    members = np.argwhere(labels == largest)
    best = members[int(np.argmin(np.hypot(members[:, 0] - iy, members[:, 1] - ix)))]
    requested = int(labels[iy, ix])
    report = {
        "components": int(np.count_nonzero(sizes)),
        "largest_cells": int(sizes[largest]),
        "largest_fraction_of_walkable": float(sizes[largest] / sizes.sum()),
        "requested_cell_component_cells": int(sizes[requested]) if requested >= 0 else 0,
        "shift_cells": float(np.hypot(best[0] - iy, best[1] - ix)),
    }
    return (int(best[0]), int(best[1])), report


@dataclass(frozen=True, eq=False)
class WalkbackField:
    """Time-optimal return to the nearest shelter for every cell (shape = grid)."""

    time_s: np.ndarray  # mean μ_W; inf = no walkable path
    var_s2: np.ndarray  # Σσ_e² along the path
    energy_per_kg_j: np.ndarray  # walking energy per kg of (W+L)
    distance_m: np.ndarray  # horizontal length of the time-optimal path (suit cost per metre, D010)
    next_hop: np.ndarray  # flat index of the next cell toward shelter; -1 at shelters/unreachable

    @property
    def sigma_s(self) -> np.ndarray:
        return np.sqrt(self.var_s2)

    def risk_factor(self, z: float = 1.645, sigma_theta: float = 0.2) -> np.ndarray:
        """W_ε / μ_W with W_ε = μ + z·sqrt(Σσ² + (σ_θ μ)²); 1 at the shelter."""
        mu = self.time_s
        with np.errstate(divide="ignore", invalid="ignore"):
            factor = 1.0 + z * np.sqrt(self.var_s2 / mu**2 + sigma_theta**2)
        return np.where(mu > 0.0, factor, 1.0)

    def time_eps_s(self, z: float = 1.645, sigma_theta: float = 0.2) -> np.ndarray:
        mu = self.time_s
        return np.where(np.isfinite(mu), mu + z * np.sqrt(self.var_s2 + (sigma_theta * mu) ** 2), np.inf)

    def consumables(self, crew: CrewMember, suit: SuitModel, model: WalkModel, *, risk: bool = True,
                    z: float = 1.645, sigma_theta: float = 0.2) -> Consumables:
        """Return needs per cell; with `risk` they scale by the same factor as time (W_ε/μ_W)."""
        mean = path_consumables(self.time_s, self.energy_per_kg_j, self.distance_m, crew, suit, model)
        return mean.scaled(self.risk_factor(z, sigma_theta)) if risk else mean


def _flat_cells(terrain: PreparedTerrain, cells: Sequence[tuple[int, int]]) -> np.ndarray:
    flat = np.array([terrain.flat_index(tuple(cell)) for cell in cells], dtype=np.int64)
    if flat.size == 0:
        raise ValueError("at least one shelter cell is required")
    return flat


def walkback(terrain: PreparedTerrain, shelters: Sequence[tuple[int, int]]) -> WalkbackField:
    sources = _flat_cells(terrain, shelters)
    if terrain.banned[sources].any():
        raise ValueError("a shelter cell is not walkable (banned)")
    dist, var, energy, travel, hop = _dijkstra(terrain.height, terrain.width, sources, True, -1,
                                               *terrain.kernel_args())
    shape = (terrain.height, terrain.width)
    return WalkbackField(dist.reshape(shape), var.reshape(shape), energy.reshape(shape), travel.reshape(shape),
                         hop.reshape(shape))


def leg_costs_from(terrain: PreparedTerrain, start: tuple[int, int],
                   goals: Sequence[tuple[int, int]]) -> list[LegCost | None]:
    """Forward time-optimal walks from one start to many goals with one full Dijkstra."""
    source = _flat_cells(terrain, [start])
    if terrain.banned[source[0]]:
        return [None] * len(goals)
    dist, var, energy, travel, _ = _dijkstra(terrain.height, terrain.width, source, False, -1,
                                             *terrain.kernel_args())
    out = []
    for goal in goals:
        g = terrain.flat_index(tuple(goal))
        out.append(LegCost(float(dist[g]), float(var[g]), float(energy[g]), float(travel[g]))
                   if math.isfinite(dist[g]) else None)
    return out


def leg_cost(terrain: PreparedTerrain, start: tuple[int, int], goal: tuple[int, int]) -> LegCost | None:
    """Forward time-optimal walk start -> goal (stops when the goal is settled)."""
    source = _flat_cells(terrain, [start])
    target = terrain.flat_index(tuple(goal))
    if terrain.banned[source[0]] or terrain.banned[target]:
        return None
    dist, var, energy, travel, _ = _dijkstra(terrain.height, terrain.width, source, False, target,
                                             *terrain.kernel_args())
    if not math.isfinite(dist[target]):
        return None
    return LegCost(float(dist[target]), float(var[target]), float(energy[target]), float(travel[target]))


def leg_path(terrain: PreparedTerrain, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
    """Cells of the forward time-optimal walk start -> goal (both included), or None."""
    source = _flat_cells(terrain, [start])
    target = terrain.flat_index(tuple(goal))
    if terrain.banned[source[0]] or terrain.banned[target]:
        return None
    dist, _, _, _, hop = _dijkstra(terrain.height, terrain.width, source, False, target, *terrain.kernel_args())
    if not math.isfinite(dist[target]):
        return None
    path, cur = [], target
    while cur != source[0]:
        path.append(divmod(int(cur), terrain.width))
        cur = int(hop[cur])
    path.append(divmod(int(source[0]), terrain.width))
    return path[::-1]


def return_path(field: WalkbackField, cell: tuple[int, int]) -> list[tuple[int, int]] | None:
    """Cells from `cell` back to the shelter along the return field's next hops."""
    if not math.isfinite(field.time_s[cell]):
        return None
    width = field.time_s.shape[1]
    path, cur = [tuple(cell)], tuple(cell)
    while field.next_hop[cur] >= 0:
        cur = divmod(int(field.next_hop[cur]), width)
        path.append(cur)
    return path
