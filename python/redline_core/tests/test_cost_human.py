"""proje.md §7.2. Expected values are hand-derived from the spec formulas."""
from dataclasses import replace

import numpy as np
import pytest

from core_helpers import terrain_grid
from redline_core.cost_human import (
    DETECTED,
    NOT_DETECTED_LIMITED,
    UNOBSERVED,
    CrewMember,
    SuitModel,
    WalkModel,
    consumables_from_energy,
    edge_cost,
    metabolic_power,
    station_power_w,
    suit_energy_per_m_j,
    suit_power_w,
    prepare_terrain,
    walking_speed,
)

CREW = CrewMember("EV1", body_mass_kg=70.0, load_mass_kg=35.0, theta=1.0)
T_FLAT_4M = 4.641338879174768  # 4 m / v(0)


@pytest.mark.parametrize(
    ("grade", "speed"),
    [
        (-0.05, 1.0266401550271307),  # Tobler optimum, slightly downhill
        (0.0, 0.8618202859411123),
        (0.1, 0.6073144909806777),
        (-0.1, 0.8618202859411123),  # symmetric about -0.05
        (0.2, 0.42796728850766663),
    ],
)
def test_walking_speed_is_tobler_scaled_by_froude(grade, speed):
    assert walking_speed(grade, WalkModel()) == pytest.approx(speed, rel=1e-12)


def test_walking_speed_is_capped_by_walk_run_transition():
    # v_wr = sqrt(0.5 · 3.721 · 0.5) is below the Tobler optimum for a 0.5 m leg.
    model = WalkModel(leg_length_m=0.5)
    assert walking_speed(-0.05, model) == pytest.approx(0.9644946863513557, rel=1e-12)


@pytest.mark.parametrize(
    ("grade_percent", "power_w"),
    # D010: suit cost 335·0.0134·W·v (314.23 W at 1 m/s for W = 70 kg).
    [(0.0, 474.07823670264906), (10.0, 613.5211147496885), (-10.0, 515.9111001167608)],
)
def test_metabolic_power_pandolf_mars_scaling(grade_percent, power_w):
    m = metabolic_power(1.0, grade_percent, 1.0, CREW, SuitModel(), WalkModel())
    assert m == pytest.approx(power_w, rel=1e-12)


def test_downhill_grade_cost_is_kd_fraction_of_uphill_cost():
    flat = metabolic_power(1.0, 0.0, 1.0, CREW, SuitModel(), WalkModel())
    up = metabolic_power(1.0, 10.0, 1.0, CREW, SuitModel(), WalkModel())
    down = metabolic_power(1.0, -10.0, 1.0, CREW, SuitModel(), WalkModel())
    assert (down - flat) / (up - flat) == pytest.approx(0.3, rel=1e-12)


def test_terrain_factor_scales_only_the_walking_term():
    m = metabolic_power(1.0, 0.0, 2.1, CREW, SuitModel(), WalkModel())
    assert m == pytest.approx(561.994766889106, rel=1e-12)


def test_theta_scales_pandolf_bracket_but_not_suit_cost():
    m = metabolic_power(1.0, 0.0, 1.0, replace(CREW, theta=1.2), SuitModel(), WalkModel())
    assert m == pytest.approx(506.0478840431789, rel=1e-12)


def test_suit_cost_is_per_metre_zero_when_standing_and_station_adds_the_task_increment():
    suit = SuitModel()
    assert suit_power_w(CREW, suit, 0.0) == 0.0
    assert suit_energy_per_m_j(CREW, suit) == pytest.approx(335.0 * 0.0134 * 70.0, rel=1e-12)
    np.testing.assert_allclose(suit_power_w(CREW, suit, np.array([0.5, 1.0])), [157.115, 314.23], rtol=1e-12)
    standing = metabolic_power(0.0, 0.0, 1.0, CREW, suit, WalkModel())
    assert standing == pytest.approx(79.92411835132452, rel=1e-12)  # Pandolf V = 0 only
    assert station_power_w(CREW, suit, WalkModel()) == pytest.approx(79.92411835132452 + 187.6, rel=1e-12)


def test_suit_speed_coefficient_reproduces_the_ewt_mars_fit():
    # EWT Table 5 (NASA/TP-2009-214796), 3/8 g non-weight suit cost; stage speeds = unsuited
    # Mars PTS mean 1.735 m/s (Table 4) minus 0.49 / 0.36 / 0.22 m/s (Table 3).
    speeds = np.array([1.245, 1.375, 1.515])
    cost = np.array([14.9, 18.8, 21.6])
    fit = float(speeds @ cost / (speeds @ speeds))  # least squares through the origin
    assert SuitModel().suit_vo2_per_speed == pytest.approx(fit, abs=0.05)
    assert np.max(np.abs(fit * speeds - cost)) < 2.0  # ml/kg/min residuals


def test_consumables_from_metabolic_energy():
    used = consumables_from_energy(500.0 * 3600.0, 3600.0, SuitModel())  # 500 W for one hour
    assert used.o2_kg == pytest.approx(0.128, rel=1e-12)
    assert used.water_kg == pytest.approx(0.5877551020408164, rel=1e-12)
    assert used.battery_wh == pytest.approx(85.0, rel=1e-12)
    assert used.co2_kg == pytest.approx(0.14963791142167832, rel=1e-12)


@pytest.mark.parametrize(
    ("state", "time_s"),
    [
        (DETECTED, T_FLAT_4M),
        (UNOBSERVED, T_FLAT_4M / 0.7),
        (NOT_DETECTED_LIMITED, T_FLAT_4M / 0.85),
    ],
)
def test_flat_edge_time_depends_on_observation_state(state, time_s):
    terrain = prepare_terrain(terrain_grid(np.zeros((1, 2)), state=state), WalkModel())
    assert edge_cost(terrain, (0, 0), (0, 1)).time_s == pytest.approx(time_s, rel=1e-12)


def test_edge_time_splits_between_the_two_cells_it_crosses():
    state = np.array([[UNOBSERVED, DETECTED]], dtype=np.uint8)
    terrain = prepare_terrain(terrain_grid(np.zeros((1, 2)), state=state), WalkModel())
    assert edge_cost(terrain, (0, 0), (0, 1)).time_s == pytest.approx(5.63591149614079, rel=1e-12)


def test_knight_edge_splits_length_equally_over_four_cells():
    state = np.full((3, 3), DETECTED, dtype=np.uint8)
    state[1, 1] = UNOBSERVED  # one of the two intermediate cells of (0,0) -> (1,2)
    terrain = prepare_terrain(terrain_grid(np.zeros((3, 3)), state=state), WalkModel())
    assert edge_cost(terrain, (0, 0), (1, 2)).time_s == pytest.approx(11.490315230495407, rel=1e-12)


def test_edge_time_sigma_comes_from_slope_sigma_and_unknown_penalty():
    model = WalkModel()
    known = prepare_terrain(terrain_grid(np.zeros((1, 2)), sigma_deg=2.0), model)
    unknown = prepare_terrain(
        terrain_grid(np.zeros((1, 2)), sigma_deg=2.0, state=UNOBSERVED), model
    )
    assert np.sqrt(edge_cost(known, (0, 0), (0, 1)).var_s2) == pytest.approx(0.603140223535358, rel=1e-12)
    assert np.sqrt(edge_cost(unknown, (0, 0), (0, 1)).var_s2) == pytest.approx(1.2924433361471959, rel=1e-12)


def test_edge_walking_energy_per_kg():
    terrain = prepare_terrain(terrain_grid(np.zeros((1, 2))), WalkModel())
    assert edge_cost(terrain, (0, 0), (0, 1)).energy_per_kg_j == pytest.approx(2.6240086297573257, rel=1e-12)


@pytest.mark.parametrize(
    ("start", "offset", "energy"),
    [
        ((0, 0), (0, 1), 7.161217268596328),  # uphill, G = +10 %: full grade term
        ((0, 1), (0, -1), 4.2176415217234915),  # downhill, G = -10 %: k_d = 0.3 of it
    ],
)
def test_edge_walking_energy_uses_directional_pandolf_grade_terms(start, offset, energy):
    terrain = prepare_terrain(terrain_grid(np.array([[0.0, 0.4]])), WalkModel())
    assert edge_cost(terrain, start, offset).energy_per_kg_j == pytest.approx(energy, rel=1e-12)


def test_rock_risk_adds_expected_detour_time_and_its_energy():
    rocks = {"rock_n_ge_per_m2": np.full((1, 2), 0.1)}
    plain = edge_cost(prepare_terrain(terrain_grid(np.zeros((1, 2))), WalkModel()), (0, 0), (0, 1))
    terrain = prepare_terrain(terrain_grid(np.zeros((1, 2)), extra=rocks), WalkModel(rock_detour_s=20.0))
    rocky = edge_cost(terrain, (0, 0), (0, 1))
    assert rocky.time_s == pytest.approx(T_FLAT_4M + 4.8, rel=1e-12)  # 20 s · 0.1 m⁻² · 0.6 m · 4 m
    assert rocky.energy_per_kg_j / plain.energy_per_kg_j == pytest.approx(rocky.time_s / plain.time_s, rel=1e-12)


def test_rock_layer_requires_explicit_detour_penalty():
    rocks = {"rock_n_ge_per_m2": np.full((1, 2), 0.1)}
    with pytest.raises(ValueError, match="rock_detour_s"):
        prepare_terrain(terrain_grid(np.zeros((1, 2)), extra=rocks), WalkModel())


@pytest.mark.parametrize(("sigma", "banned"), [(2.0, True), (1.5, False)])
def test_cell_is_banned_when_slope_plus_z_sigma_exceeds_limit(sigma, banned):
    terrain = prepare_terrain(terrain_grid(np.zeros((1, 1)), slope_deg=22.0, sigma_deg=sigma), WalkModel())
    assert bool(terrain.banned_mask[0, 0]) is banned


@pytest.mark.parametrize(("relief", "banned"), [(1.0, True), (0.5, False)])
def test_ridge_wall_is_banned(relief, banned):
    grid = terrain_grid(np.zeros((1, 1)), slope_deg=20.0, relief_m=relief, wall_slope_deg=35.0)
    assert bool(prepare_terrain(grid, WalkModel()).banned_mask[0, 0]) is banned


def test_missing_slope_sigma_is_never_treated_as_zero():
    grid = terrain_grid(np.zeros((1, 1)), slope_deg=22.0, sigma_deg=np.nan)
    with pytest.raises(ValueError, match="sigma"):
        prepare_terrain(grid, WalkModel())
    # With an explicit fallback of 3°: 22 + 1.645·3 = 26.9° > 25° -> banned.
    terrain = prepare_terrain(grid, WalkModel(), sigma_fallback_deg=3.0)
    assert bool(terrain.banned_mask[0, 0]) is True
    assert terrain.sigma_fallback_cells == 1


def test_cells_without_elevation_are_banned():
    z = np.array([[0.0, np.nan]])
    terrain = prepare_terrain(terrain_grid(z), WalkModel())
    assert terrain.banned_mask.tolist() == [[False, True]]
    assert edge_cost(terrain, (0, 0), (0, 1)) is None


def test_unknown_state_code_is_rejected():
    with pytest.raises(ValueError, match="state"):
        prepare_terrain(terrain_grid(np.zeros((1, 1)), state=7), WalkModel())


def test_knight_edge_cannot_jump_over_a_banned_cell():
    slope = np.zeros((3, 3))
    slope[0, 1] = 40.0  # intermediate of (0,0)->(1,2), not of (0,0)->(2,1)
    terrain = prepare_terrain(terrain_grid(np.zeros((3, 3)), slope_deg=slope), WalkModel())
    assert edge_cost(terrain, (0, 0), (1, 2)) is None
    assert edge_cost(terrain, (0, 0), (2, 1)) is not None


def test_diagonal_edge_cannot_cut_a_banned_corner():
    slope = np.zeros((2, 2))
    slope[0, 1] = 40.0
    terrain = prepare_terrain(terrain_grid(np.zeros((2, 2)), slope_deg=slope), WalkModel())
    assert edge_cost(terrain, (0, 0), (1, 1)) is None
    assert edge_cost(terrain, (0, 0), (1, 0)) is not None


def test_edge_steeper_than_limit_is_removed_even_if_cells_look_flat():
    # 3 m rise over 4 m: 36.9° along the edge.
    terrain = prepare_terrain(terrain_grid(np.array([[0.0, 3.0]])), WalkModel())
    assert edge_cost(terrain, (0, 0), (0, 1)) is None
