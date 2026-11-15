"""Topographic sky view and site dose rate (proje.md §7.3).

An ALARA helper layer, not the main safety driver. Horizon angles are radians.
"""
from __future__ import annotations

import numpy as np

# Gale GCR baseline, literature value (proje.md §7.3 [K]); not a new measurement.
GALE_GCR_MGY_PER_DAY = 0.21


def f_alpha(h_cube_rad, alpha: float):
    """F = mean_k[1 - sin^(α+1)(max(h_k, 0))] over the last (azimuth) axis."""
    h = np.asarray(h_cube_rad, dtype=float)
    if h.ndim == 0 or h.shape[-1] == 0:
        raise ValueError("horizon cube needs at least one azimuth on its last axis")
    if not np.isfinite(alpha) or alpha < 0:
        raise ValueError("alpha must be finite and >= 0")
    if (h > np.pi / 2).any():
        raise ValueError("horizon angles must be <= π/2 radians")
    f = np.mean(1.0 - np.sin(np.maximum(h, 0.0)) ** (alpha + 1.0), axis=-1)
    return float(f) if f.ndim == 0 else f


def dose_rate_site(d_open, sky_view, f_a: float = 0.2):
    """d_site = d_open·((1 - f_a)·F + f_a); f_a is the isotropic fraction."""
    if not 0.0 <= f_a <= 1.0:
        raise ValueError("f_a must be within [0, 1]")
    out = d_open * ((1.0 - f_a) * np.asarray(sky_view, dtype=float) + f_a)
    return float(out) if np.ndim(out) == 0 else out
