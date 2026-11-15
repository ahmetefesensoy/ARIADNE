"""Golombek rock abundance model (proje.md §7.4).

Sampled rocks are SCENARIO decoration/navigation objects below DEM resolution,
never ARCHIVE measurements.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import exp1

K_BOUNDS = (0.005, 0.3)


def q_of_k(k):
    return 1.79 + 0.152 / np.asarray(k, dtype=float)


def area_fraction_ge(d_m, k):
    """F_k(D) = k·exp(-q·D): fraction of area covered by rocks with diameter >= D."""
    return k * np.exp(-q_of_k(k) * np.asarray(d_m, dtype=float))


def n_ge(d_m, k):
    """Rocks per m² with diameter >= D: (4kq/π)·[exp(-qD)/D - q·E1(qD)]."""
    d = np.asarray(d_m, dtype=float)
    if (d <= 0).any():
        raise ValueError("diameter must be > 0")
    q = q_of_k(k)
    out = (4.0 * k * q / np.pi) * (np.exp(-q * d) / d - q * exp1(q * d))
    return float(out) if out.ndim == 0 else out


def _log_number_density(d, k):
    q = q_of_k(k)
    return np.log(4.0 * k * q / np.pi) - q * d - 2.0 * np.log(d)


def fit_k(diameters_m, area_m2: float, d_min_m: float, bounds: tuple[float, float] = K_BOUNDS) -> float:
    """Maximum-likelihood k from detected diameters >= d_min (Poisson process)."""
    if area_m2 <= 0 or d_min_m <= 0:
        raise ValueError("area and d_min must be > 0")
    d = np.asarray(diameters_m, dtype=float)
    d = d[d >= d_min_m]

    def negative_log_likelihood(k):
        return -(np.sum(_log_number_density(d, k)) - area_m2 * n_ge(d_min_m, k))

    result = minimize_scalar(negative_log_likelihood, bounds=bounds, method="bounded", options={"xatol": 1e-7})
    return float(result.x)


def sample_rocks(k: float, area_m2: float, d_range_m: tuple[float, float], seed: int) -> np.ndarray:
    """SCENARIO diameters in [d_min, d_max] for an area, reproducible from the seed."""
    d_min, d_max = d_range_m
    if not 0 < d_min < d_max:
        raise ValueError("d_range must satisfy 0 < d_min < d_max")
    rng = np.random.default_rng(seed)
    total = n_ge(d_min, k) - n_ge(d_max, k)
    count = rng.poisson(area_m2 * total)
    sizes = np.geomspace(d_min, d_max, 4096)
    cdf = (n_ge(d_min, k) - n_ge(sizes, k)) / total
    return np.interp(rng.random(count), cdf, sizes)
