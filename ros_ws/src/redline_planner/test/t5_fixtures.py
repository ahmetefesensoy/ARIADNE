"""Synthetic T5 inputs for node tests (SIMULATED test data, not a site product).

A flat 60×60 grid at 4 m around the map origin; the habitat request (0, 0)
falls in cell (30, 30) whose centre is (2, 2) m.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.grid import Grid
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid, save_planning_grid

ORIGIN = (-120.0, -120.0)
SHAPE = (60, 60)
HABITAT_XY = (2.0, 2.0)
EVA = """provenance_status: SCENARIO
site_id: TST
crew_ids: [EV1]
habitat: {requested_xy_m: [0.0, 0.0], placement: nearest_in_largest_component}
reserve: {o2_kg: 0.1, co2_capacity_kg: 0.0, water_kg: 0.0, battery_wh: 0.0}
start: {minutes_above_reserve: 60.0}
lines: {terminate_threshold_min: 10.0, simplify_tolerance_m: 4.0, min_hole_area_m2: 0.0}
tile: {lo_min: -60.0, hi_min: 60.0, bit_depth: 8}
sigma_fallback_percentile: 95.0
"""


def write_inputs(directory: Path) -> dict[str, str]:
    layers = {"z_m": np.zeros(SHAPE), "slope_deg": np.zeros(SHAPE), "slope_sigma_deg": np.full(SHAPE, 0.5),
              "relief_m": np.zeros(SHAPE), "wall_slope_deg": np.zeros(SHAPE)}
    save_planning_grid(directory / "grid", Grid(ORIGIN, 4.0, SHAPE[1], SHAPE[0], layers),
                       {"status": "SIMULATED", "site_id": "TST", "note": "synthetic flat test grid"})
    (directory / "crew.yaml").write_text(
        "provenance_status: SCENARIO\ncrew:\n  EV1: {body_mass_kg: 75.0, load_mass_kg: 80.0, theta: 1.0}\n")
    (directory / "suit.yaml").write_text("provenance_status: SCENARIO\nwalk: {}\nsuit: {}\n")
    (directory / "eva.yaml").write_text(EVA)
    return {"planning_grid": str(directory / "grid.npz"), "crew_file": str(directory / "crew.yaml"),
            "suit_file": str(directory / "suit.yaml"), "eva_file": str(directory / "eva.yaml")}


def reference_model(paths: dict[str, str]) -> ReturnFieldModel:
    grid, _ = load_planning_grid(paths["planning_grid"])
    walk, suit = load_models(paths["suit_file"])
    return ReturnFieldModel(grid, walk, suit, load_crew(paths["crew_file"]), load_eva(paths["eva_file"]))


def flat_index(x: float, y: float) -> int:
    ix = int((x - ORIGIN[0]) // 4.0)
    iy = int((y - ORIGIN[1]) // 4.0)
    return iy * SHAPE[1] + ix


def spin_until(executor, predicate, timeout_s: float) -> bool:
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        executor.spin_once(timeout_sec=0.02)
        if predicate():
            return True
    return False
