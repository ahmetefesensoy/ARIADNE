"""Time to shelter and pressurised-rover station planning (proje.md §7.7)."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class StationPlan:
    value_s: float  # bottleneck: worst rescue time over all segments
    stations: tuple[int, ...]  # rover station index per segment; () if infeasible
    distance_m: float  # total rover distance (tie-break)


def shelter_time(walk_time_to_pr_s, rover_time_s, tau_al_s: float = 300.0):
    """T_sh(x) = min(W_time_to_PR(x), T_rover(PR→x) + τ_al)."""
    return np.minimum(np.asarray(walk_time_to_pr_s, dtype=float), np.asarray(rover_time_s, dtype=float) + tau_al_s)


def kappa_matrix(rescue_s, segments: Sequence[Sequence[int]], los=None, rho: float = 0.0) -> np.ndarray:
    """κ(k, c) = max_{x∈X_k} R_c(x); ∞ when station c sees less than ρ of segment k."""
    rescue = np.asarray(rescue_s, dtype=float)  # stations × crew positions
    kappa = np.full((len(segments), rescue.shape[0]), math.inf)
    for k, members in enumerate(segments):
        idx = np.asarray(members, dtype=int)
        if idx.size == 0:
            raise ValueError(f"segment {k} has no crew positions")
        worst = rescue[:, idx].max(axis=1)
        if los is not None:
            seen = np.asarray(los, dtype=bool)[:, idx].mean(axis=1)
            worst = np.where(seen < rho, math.inf, worst)
        kappa[k] = worst
    return kappa


def bottleneck_plan(kappa, rover_time, dt_s, distance) -> StationPlan:
    """Bottleneck DP B_k(c) = max(κ(k,c), min_{c': T_R(c',c) ≤ Δt_k} B_{k-1}(c')),
    then the minimum rover distance among sequences achieving the optimum."""
    kappa = np.asarray(kappa, dtype=float)
    rover_time = np.asarray(rover_time, dtype=float)
    distance = np.asarray(distance, dtype=float)
    dt = np.asarray(dt_s, dtype=float)
    k_count, c_count = kappa.shape
    if rover_time.shape != (c_count, c_count) or distance.shape != (c_count, c_count) or dt.shape != (k_count,):
        raise ValueError("rover_time/distance must be C×C and dt_s must have K entries")
    allowed = [None] + [rover_time <= dt[k] for k in range(1, k_count)]  # [from c', to c]

    best = kappa[0].copy()
    for k in range(1, k_count):
        reachable = np.where(allowed[k], best[:, None], math.inf).min(axis=0)
        best = np.maximum(kappa[k], reachable)
    value = float(best.min())
    if not math.isfinite(value):
        return StationPlan(math.inf, (), math.inf)

    # Exact tie-break: every sequence with all κ ≤ value is optimal; minimise distance.
    usable = kappa <= value
    total = np.where(usable[0], 0.0, math.inf)
    parents = []
    columns = np.arange(c_count)
    for k in range(1, k_count):
        candidate = np.where(allowed[k] & usable[k][None, :], total[:, None] + distance, math.inf)
        parent = candidate.argmin(axis=0)
        total = candidate[parent, columns]
        parents.append(parent)
    end = int(total.argmin())
    sequence = [end]
    for parent in reversed(parents):
        sequence.append(int(parent[sequence[-1]]))
    sequence.reverse()
    return StationPlan(value, tuple(sequence), float(total[end]))
