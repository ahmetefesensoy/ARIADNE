"""Hidden SCENARIO truth (spec scenario_rocks_<seed>.json; D015): format, blocked rule, survey model."""
import json

import numpy as np
import pytest

from core_helpers import terrain_grid
from redline_core.truth import (TRUTH_SCHEMA, Obstacle, blocked_cells, load_truth, scenario_world,
                                survey_evidence, write_truth)


def grid():
    return terrain_grid(np.zeros((20, 30)), 4.0)  # origin (0, 0); cell (iy, ix) centre (4ix+2, 4iy+2)


def test_world_is_deterministic_per_seed_and_round_trips(tmp_path):
    g = grid()
    a = scenario_world(g, "TST", seed=7, k=0.05, d_range_m=(0.3, 3.0),
                       obstacles=[Obstacle("O1", 42.0, 42.0, 6.0)])
    b = scenario_world(g, "TST", seed=7, k=0.05, d_range_m=(0.3, 3.0),
                       obstacles=[Obstacle("O1", 42.0, 42.0, 6.0)])
    assert a == b and a["schema"] == TRUTH_SCHEMA and a["status"] == "SCENARIO" and a["rocks"]
    assert {r["class"] for r in a["rocks"]} <= {"decor", "navigation"}
    path = write_truth(a, tmp_path / "scenario_rocks_7.json")
    assert load_truth(path) == a
    bad = dict(a, schema="other")
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="schema"):
        load_truth(tmp_path / "bad.json")


def test_blocked_cells_are_obstacle_discs_and_cells_with_large_rocks():
    g = grid()
    world = scenario_world(g, "TST", seed=1, k=0.0, d_range_m=(0.3, 3.0), obstacles=[Obstacle("O1", 42.0, 42.0, 4.0)])
    world["rocks"] = [{"x": 10.0, "y": 10.0, "d_m": 2.5, "class": "navigation"},
                      {"x": 90.0, "y": 10.0, "d_m": 0.8, "class": "navigation"}]
    cells = blocked_cells(world, g, d_block_m=2.0)
    disc = {(iy, ix) for iy in range(20) for ix in range(30)
            if np.hypot(4 * ix + 2 - 42.0, 4 * iy + 2 - 42.0) <= 4.0}
    assert disc | {(2, 2)} == cells  # (10, 10) m lies in cell (2, 2); the 0.8 m rock does not block


def test_survey_marks_blocked_cells_and_hides_features_below_the_detection_limit():
    g = grid()
    world = scenario_world(g, "TST", seed=1, k=0.0, d_range_m=(0.3, 3.0),
                           obstacles=[Obstacle("O1", 42.0, 42.0, 4.0), Obstacle("SMALL", 90.0, 42.0, 0.5)])
    polygon = [(20.0, 20.0), (110.0, 20.0), (110.0, 60.0), (20.0, 60.0)]
    records = survey_evidence(world, g, polygon, spacing_m=8.0, detection_limit_m=2.0, d_block_m=2.0)
    blocked = {g.cell_index(x, y) for x, y, _, passable in records if not passable}
    assert blocked == blocked_cells({**world, "obstacles": world["obstacles"][:1]}, g, d_block_m=2.0)
    assert all(r > 0 for _, _, r, _ in records) and any(p for *_, p in records)
    inside = [(x, y) for x, y, _, p in records if p]
    assert all(20.0 <= x <= 110.0 and 20.0 <= y <= 60.0 for x, y in inside)
