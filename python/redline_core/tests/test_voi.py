"""Robot observation value (§7.11): on-path gain, far cells, blocked risk, budget, ranking."""
import numpy as np
import pytest

from core_helpers import terrain_grid
from redline_core.cost_human import UNOBSERVED, CrewMember, SuitModel, WalkModel
from redline_core.field_model import EvaConfig, ReturnFieldModel
from redline_core.orienteering import Candidate, RoutePlanner
from redline_core.redline import Resources
from redline_core.science_value import ScienceModel
from redline_core.voi import VoiEstimator

WALK, SUIT = WalkModel(), SuitModel()
CREW = {"EV1": CrewMember("EV1", 75.0, 80.0)}
SCIENCE = ScienceModel("TST", "q", ("H1", "H2"), np.array([0.5, 0.5]),
                       {"ridge": np.array([0.9, 0.1]), "hollow": np.array([0.9, 0.1])})


def build(density=0.0):
    grid = terrain_grid(np.zeros((60, 60)), 4.0, state=UNOBSERVED)
    eva = EvaConfig("TST", ("EV1",), (122.0, 122.0), Resources(0.1, 0.0, 0.0, 0.0), 120.0, 30.0, 95.0,
                    -60.0, 60.0, 8, 0.0, habitat_placement="fixed")
    model = ReturnFieldModel(grid, WALK, SUIT, CREW, eva)  # habitat cell (30, 30)
    candidates = [Candidate("A", (30, 50), "ridge", 600.0), Candidate("B", (50, 50), "hollow", 600.0)]
    planner = RoutePlanner(model.terrain, model.field, model.habitat_cell, candidates, SCIENCE, SCIENCE.prior,
                           CREW["EV1"], SUIT, WALK, model.start_resources("EV1"), model.reserve, 4 * 3600.0)
    route = planner.heuristic("SCIENCE")
    assert route.valid and len(route.order) == 2
    return VoiEstimator(model, planner, route, obstacle_density_per_km2=density, robot_speed_m_s=0.1,
                        inspect_s=300.0)


def test_observing_cells_on_the_path_raises_the_plan_margin():
    est = build()
    on_path = est.paths[0].cells[len(est.paths[0].cells) // 2]
    near = est.evaluate(on_path)
    assert near.p_open == 1.0 and near.voi_s > 0.0 and near.score > 0.0
    far = est.evaluate((5, 5))  # well away from every planned walk
    assert far.voi_s <= near.voi_s * 0.1 + 1e-9


def test_a_likely_blocked_footprint_on_the_path_ranks_first_with_positive_value():
    # D015: the old VOI scored this case 0; with late discovery priced in it must rank first.
    est = build(density=20000.0)  # p_block = 1 - exp(-0.02 /m² · A_footprint) ≈ 0.9 for a 6 m footprint
    cell = est.paths[0].cells[len(est.paths[0].cells) // 2]
    result = est.evaluate(cell)
    assert result.p_open < 0.2
    assert result.margin_late_s <= result.margin_blocked_s <= result.margin_now_s <= result.margin_open_s
    assert result.voi_s > 0.0 and result.score > 0.0
    assert result.legacy_voi_s < 0.0  # the spec-literal value it replaces, kept as a diagnostic
    far = est.evaluate((5, 5))
    assert far.voi_s < result.voi_s


def test_voi_is_the_two_outcome_formula_and_never_negative():
    for density in (0.0, 500.0, 5000.0, 50000.0):
        est = build(density=density)
        cells = est.candidate_cells()[::7][:12] + [est.paths[0].cells[len(est.paths[0].cells) // 2]]
        for cell in cells:
            r = est.evaluate(cell)
            p = 1.0 - r.p_open
            assert r.voi_s >= 0.0
            expected = (1 - p) * (r.margin_open_s - r.margin_now_s) + (
                p * (r.margin_blocked_s - r.margin_late_s) if p > 0 else 0.0)
            assert r.voi_s == pytest.approx(expected, abs=1e-6)


def test_p_block_follows_the_obstacle_density_and_footprint_area():
    est = build(density=1000.0)
    cell = est.paths[0].cells[len(est.paths[0].cells) // 2]
    area = len(est.footprint(cell)) * est.grid.resolution_m ** 2
    assert est.evaluate(cell).p_open == pytest.approx(np.exp(-1000.0e-6 * area), rel=1e-12)


def test_evaluation_fits_the_50_ms_budget_and_ranking_is_sorted():
    est = build()
    cells = est.candidate_cells()
    assert len(cells) > 10 and all(est.model.state[c] == UNOBSERVED for c in cells)
    est.evaluate(cells[0])  # numba warm-up
    times = [est.evaluate(c).compute_ms for c in cells[:20]]
    assert np.median(times) <= 50.0
    top = est.rank(k=3)
    assert len(top) == 3 and top[0].score >= top[1].score >= top[2].score
    assert top[0].robot_cost_s >= 300.0
