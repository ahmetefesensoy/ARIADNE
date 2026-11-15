"""Orienteering (§7.9): validity, windows, Pareto objectives, heuristic vs exact gap."""
import math

import numpy as np
import pytest

from core_helpers import terrain_grid
from redline_core.cost_human import UNOBSERVED, CrewMember, SuitModel, WalkModel, prepare_terrain
from redline_core.field_model import EvaConfig, start_resources
from redline_core.orienteering import Candidate, RoutePlanner
from redline_core.redline import Resources
from redline_core.science_value import ScienceModel
from redline_core.walkback import walkback

WALK, SUIT = WalkModel(), SuitModel()
CREW = CrewMember("EV1", 75.0, 80.0)
SCIENCE = ScienceModel("TST", "q", ("H1", "H2", "H3"), np.array([1 / 3] * 3),
                       {"ridge": np.array([0.85, 0.15, 0.5]), "hollow": np.array([0.9, 0.2, 0.5])})
HABITAT = (20, 20)


def setup(candidates, budget_min=120.0, max_duration_h=4.0, **kwargs):
    grid = terrain_grid(np.zeros((41, 41)), 4.0, state=UNOBSERVED)
    terrain = prepare_terrain(grid, WALK)
    field = walkback(terrain, [HABITAT])
    eva = EvaConfig("TST", ("EV1",), (82.0, 82.0), Resources(0.1, 0.0, 0.0, 0.0), budget_min, 30.0, 95.0,
                    -60.0, 60.0, 8, 0.0)
    initial = start_resources(CREW, SUIT, WALK, eva)
    return RoutePlanner(terrain, field, HABITAT, candidates, SCIENCE, SCIENCE.prior, CREW, SUIT, WALK, initial,
                        eva.reserve, max_duration_h * 3600.0, **kwargs)


def ring_of_candidates():
    spots = [((20, 30), "ridge"), ((30, 20), "hollow"), ((10, 20), "ridge"), ((20, 8), "hollow"),
             ((34, 34), "ridge"), ((6, 6), "hollow")]
    return [Candidate(f"T{i}", cell, cls, 600.0) for i, (cell, cls) in enumerate(spots)]


def test_route_evaluation_accounts_walk_service_and_return():
    planner = setup(ring_of_candidates())
    empty = planner.evaluate(())
    assert empty.valid and empty.duration_s == 0.0 and empty.value_bits == 0.0
    one = planner.evaluate((0,))
    leg = planner.legs[(0, 1)].time_s
    back = planner.field.time_s[0, 1]
    assert one.valid and one.duration_s == pytest.approx(leg + 600.0 + back)
    assert one.value_bits > 0 and one.min_margin_s > 0


def test_heuristic_matches_exact_on_a_small_instance_and_objectives_differ():
    planner = setup(ring_of_candidates())
    result = planner.pareto()
    for objective in ("SCIENCE", "SAFE", "FAST"):
        entry = result[objective]
        assert entry["route"].valid and entry["exact"].valid
        assert entry["gap"] is not None and entry["gap"] <= 0.05
    sci, safe, fast = (result[k]["route"] for k in ("SCIENCE", "SAFE", "FAST"))
    floor = result["SAFE"]["floor_bits"]
    assert safe.value_bits >= floor - 1e-12 and fast.value_bits >= floor - 1e-12
    assert fast.duration_s <= sci.duration_s
    assert safe.min_margin_s >= sci.min_margin_s - 1e-9


def test_a_closed_window_excludes_the_station():
    candidates = ring_of_candidates()
    candidates[0] = Candidate("T0", (20, 30), "ridge", 600.0, window_open_s=0.0, window_close_s=10.0)
    planner = setup(candidates)
    best = planner.heuristic("SCIENCE")
    assert 0 not in best.order
    assert not planner.evaluate((0,)).valid


def test_an_early_arrival_waits_for_the_window():
    candidates = ring_of_candidates()
    candidates[0] = Candidate("T0", (20, 30), "ridge", 600.0, window_open_s=1800.0)
    planner = setup(candidates)
    ev = planner.evaluate((0,))
    assert ev.valid and ev.timeline.wait_s > 0
    assert ev.duration_s == pytest.approx(1800.0 + 600.0 + planner.field.time_s[0, 1])


def test_duration_limit_and_consumables_bound_the_route():
    tight = setup(ring_of_candidates(), max_duration_h=0.5)
    route = tight.heuristic("SCIENCE")
    assert route.duration_s <= 1800.0 and len(route.order) < 6
    starved = setup(ring_of_candidates(), budget_min=2.0)  # suit nearly empty at start
    assert starved.heuristic("SCIENCE").order == ()


def test_unknown_classes_and_empty_candidates_are_rejected():
    with pytest.raises(ValueError):
        setup([Candidate("X", (20, 30), "crater", 60.0)])
    with pytest.raises(ValueError):
        setup([])


def test_assembled_plan_has_marginal_values_a_return_leg_and_a_connected_path():
    from redline_core.eva_plan import assemble_plan

    grid = terrain_grid(np.zeros((41, 41)), 4.0, state=UNOBSERVED)
    terrain = prepare_terrain(grid, WALK)
    field = walkback(terrain, [HABITAT])
    planner = setup(ring_of_candidates())
    route = planner.heuristic("SCIENCE")
    plan = assemble_plan(planner, route, "SCIENCE", terrain, field, grid, HABITAT)
    assert plan.valid and len(plan.stations) == len(route.order) and len(plan.legs) == len(route.order) + 1
    assert plan.legs[-1].to_id == "HAB" and plan.legs[0].from_id == "HAB"
    assert all(s.marginal_value_bits > 0 for s in plan.stations)
    assert sum(s.marginal_value_bits for s in plan.stations) <= plan.value_bits + 1e-9  # submodular
    steps = np.hypot(*np.diff(plan.path_xyz[:, :2], axis=0).T)
    assert steps.max() <= 4.0 * np.hypot(1, 2) + 1e-9  # 16-neighbour moves only
    np.testing.assert_allclose(plan.path_xyz[0, :2], grid.cell_center(*HABITAT))
    np.testing.assert_allclose(plan.path_xyz[-1, :2], grid.cell_center(*HABITAT))


def test_global_held_karp_orders_are_minimum_time_for_every_subset():
    import itertools

    planner = setup(ring_of_candidates()[:5])
    orders = planner._min_time_orders()
    assert len(orders) == 2**5 - 1

    def walk_time(order):
        legs = [planner.legs[(a, b)].time_s for a, b in zip((0,) + tuple(i + 1 for i in order),
                                                            tuple(i + 1 for i in order))]
        return sum(legs) + planner.field.time_s[0, order[-1] + 1]

    for mask, order in orders.items():
        subset = [k for k in range(5) if (mask >> k) & 1]
        assert sorted(order) == subset
        brute = min(walk_time(p) for p in itertools.permutations(subset))
        assert walk_time(order) == pytest.approx(brute, rel=1e-12)
