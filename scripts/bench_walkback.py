"""Walkback timing on a full 3 km × 3 km, 4 m grid (proje.md §7.5 target: <= 1 s).

Two synthetic worst cases where every cell is reachable, so the whole graph is
traversed: a flat plane and a rough random surface (all cells walkable, mixed
observation states). The first call includes numba compilation/cache load and
is reported separately. Timing evidence only; not a terrain product.
"""
from __future__ import annotations

import json
import platform
import time

import numpy as np

from redline_core.cost_human import WalkModel, prepare_terrain
from redline_core.grid import Grid
from redline_core.walkback import walkback

N, RES = 750, 4.0


def grid(z, state):
    zeros = np.zeros((N, N))
    return Grid((-1500.0, -1500.0), RES, N, N, {
        "z_m": z, "slope_deg": zeros, "slope_sigma_deg": zeros + 1.0, "state": state,
        "relief_m": zeros, "wall_slope_deg": zeros,
    })


def main() -> None:
    rng = np.random.default_rng(0)
    cases = {
        "flat_detected": grid(np.zeros((N, N)), np.ones((N, N), dtype=np.uint8)),
        "rough_mixed_states": grid(rng.normal(0.0, 0.5, (N, N)), rng.integers(0, 3, (N, N)).astype(np.uint8)),
    }
    report = {"grid": f"{N}x{N} @ {RES} m", "python": platform.python_version(), "cases": {}}
    for name, g in cases.items():
        terrain = prepare_terrain(g, WalkModel())
        times = []
        for _ in range(4):
            started = time.perf_counter()
            field = walkback(terrain, [(N // 2, N // 2)])
            times.append(time.perf_counter() - started)
        report["cases"][name] = {
            "reachable_fraction": float(np.isfinite(field.time_s).mean()),
            "first_call_s": times[0],
            "steady_s": {"min": min(times[1:]), "max": max(times[1:])},
        }
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
