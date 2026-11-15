"""proje.md §7.6: margins, limiting consumable and red/yellow line contours."""
import math

import numpy as np
import pytest

from core_helpers import terrain_grid
from redline_core.cost_human import CrewMember, SuitModel, WalkModel, prepare_terrain
from redline_core.redline import (
    LIM_BATTERY,
    LIM_CO2,
    LIM_DAYLIGHT,
    LIM_NONE,
    LIM_O2,
    LIM_SHELTER,
    LIM_WATER,
    Rates,
    Resources,
    combine_crew,
    margin_for_crew,
    margins,
    region_contours,
)
from redline_core.walkback import walkback

# Return needs per cell (already risk adjusted), what is left above reserve, and the
# current consumption rate. Hand result: O2 limits everywhere at 5400/4500/1800 s.
NEEDS = {
    LIM_O2: np.array([[0.0, 0.05, 0.2]]),
    LIM_WATER: np.array([[0.0, 0.2, 0.5]]),
    LIM_BATTERY: np.array([[0.0, 30.0, 60.0]]),
    LIM_CO2: np.array([[0.0, 0.06, 0.24]]),
}
AVAILABLE = {LIM_O2: 0.3, LIM_WATER: 1.0, LIM_BATTERY: 300.0, LIM_CO2: 0.5}
RATES = {LIM_O2: 0.2 / 3600, LIM_WATER: 0.6 / 3600, LIM_BATTERY: 150.0 / 3600, LIM_CO2: 0.24 / 3600}


def test_margin_is_time_to_exhaust_the_most_limiting_consumable():
    field = margins(NEEDS, AVAILABLE, RATES)
    np.testing.assert_allclose(field.margin_s, [[5400.0, 4500.0, 1800.0]], rtol=1e-12)
    np.testing.assert_allclose(field.margin_min, [[90.0, 75.0, 30.0]], rtol=1e-12)
    np.testing.assert_array_equal(field.limiting, [[LIM_O2, LIM_O2, LIM_O2]])


def test_daylight_budget_can_become_the_limit():
    field = margins(
        NEEDS, AVAILABLE, RATES, time_need_s=np.array([[0.0, 600.0, 1500.0]]), daylight_budget_s=5000.0
    )
    np.testing.assert_allclose(field.margin_s, [[5000.0, 4400.0, 1800.0]], rtol=1e-12)
    np.testing.assert_array_equal(field.limiting, [[LIM_DAYLIGHT, LIM_DAYLIGHT, LIM_O2]])


def test_sep_mode_marks_cells_too_far_from_shelter_unsafe():
    field = margins(
        NEEDS, AVAILABLE, RATES, shelter_time_s=np.array([[100.0, 1300.0, 900.0]]), shelter_max_s=1200.0
    )
    assert field.margin_s[0, 1] == -math.inf
    assert field.limiting[0, 1] == LIM_SHELTER
    np.testing.assert_allclose(field.margin_s[0, [0, 2]], [5400.0, 1800.0], rtol=1e-12)


def test_unreachable_cell_has_no_margin_and_no_limiting_consumable():
    needs = {key: value.copy() for key, value in NEEDS.items()}
    for value in needs.values():
        value[0, 2] = math.inf
    field = margins(needs, AVAILABLE, RATES)
    assert math.isnan(field.margin_s[0, 2])
    assert field.limiting[0, 2] == LIM_NONE
    assert field.limiting[0, 0] == LIM_O2


def test_numerically_tied_consumables_resolve_to_the_lowest_code():
    # O2 and water hit zero together (same minutes left); float noise must not pick at random.
    rate_o2, rate_water = 0.2 / 3600, 0.6 / 3600
    needs = {LIM_O2: np.array([[0.1, 0.2]]), LIM_WATER: np.array([[0.3, 0.6]])}
    available = {LIM_O2: 0.3, LIM_WATER: 0.9 * (1 - 1e-15)}  # water margin a few ulp below O2
    field = margins(needs, available, {LIM_O2: rate_o2, LIM_WATER: rate_water})
    np.testing.assert_array_equal(field.limiting, [[LIM_O2, LIM_O2]])
    clear = margins(needs, {LIM_O2: 0.3, LIM_WATER: 0.89}, {LIM_O2: rate_o2, LIM_WATER: rate_water})
    np.testing.assert_array_equal(clear.limiting, [[LIM_WATER, LIM_WATER]])


def test_ties_survive_float32_transport_of_remaining_and_rates():
    # Equal minutes for O2 and water (the SCENARIO start); values rounded as a ROS message would.
    f32 = lambda v: float(np.float32(v))  # noqa: E731
    rate_o2, rate_water = 5.1e-5, 2.6e-4
    needs = {LIM_O2: np.array([[0.0, rate_o2 * 30.0]]), LIM_WATER: np.array([[0.0, rate_water * 30.0]])}
    available = {LIM_O2: f32(0.1 + rate_o2 * 3600.0) - 0.1, LIM_WATER: f32(rate_water * 3600.0)}
    rates = {LIM_O2: f32(rate_o2 * 3600.0) / 3600.0, LIM_WATER: f32(rate_water * 3600.0) / 3600.0}
    field = margins(needs, available, rates)
    np.testing.assert_array_equal(field.limiting, [[LIM_O2, LIM_O2]])


def test_consumption_rates_must_be_positive():
    with pytest.raises(ValueError, match="rate"):
        margins(NEEDS, AVAILABLE, {**RATES, LIM_WATER: 0.0})


def test_crew_line_uses_the_worse_member_per_cell():
    ev1 = margins(NEEDS, AVAILABLE, RATES)
    ev2_needs = {key: np.zeros((1, 3)) for key in NEEDS}
    ev2_needs[LIM_O2] = np.array([[0.1, 0.0, 0.0]])
    ev2 = margins(ev2_needs, AVAILABLE, RATES)  # [3600, 5400, 5400] s
    combined = combine_crew({"EV1": ev1, "EV2": ev2})
    np.testing.assert_allclose(combined.field.margin_s, [[3600.0, 4500.0, 1800.0]], rtol=1e-12)
    assert [combined.crew_ids[i] for i in combined.limiting_crew[0]] == ["EV2", "EV1", "EV1"]


def test_margin_for_crew_at_shelter_equals_available_over_rate():
    terrain = prepare_terrain(terrain_grid(np.zeros((1, 3))), WalkModel())
    crew = CrewMember("EV1", body_mass_kg=70.0, load_mass_kg=35.0)
    remaining = Resources(o2_kg=0.5, co2_capacity_kg=1.0, water_kg=2.0, battery_wh=500.0)
    reserve = Resources(o2_kg=0.1, co2_capacity_kg=0.0, water_kg=0.0, battery_wh=0.0)
    rates = Rates(o2_kg_s=0.2 / 3600, co2_kg_s=0.2 / 3600, water_kg_s=0.6 / 3600, battery_w=150.0)
    field = margin_for_crew(walkback(terrain, [(0, 0)]), crew, SuitModel(), WalkModel(), remaining, reserve, rates)
    # At the shelter nothing is needed: O2 (0.4 kg at 0.2 kg/h) gives 7200 s, the minimum.
    assert field.margin_s[0, 0] == pytest.approx(7200.0, rel=1e-12)
    assert field.limiting[0, 0] == LIM_O2
    assert field.margin_s[0, 0] > field.margin_s[0, 1] > field.margin_s[0, 2]


def signed_area(ring):
    x, y = ring[:, 0], ring[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def centred_radius(n=101, res=10.0):
    centres = (np.arange(n) - n // 2) * res
    xx, yy = np.meshgrid(centres, centres)  # row index increases with y (north)
    origin = (-(n // 2) * res - res / 2, -(n // 2) * res - res / 2)
    return np.hypot(xx, yy), origin, res


def test_red_line_contour_closes_around_the_safe_region():
    radius, origin, res = centred_radius()
    rings = region_contours(300.0 - radius, origin, res, 0.0)
    assert len(rings) == 1
    ring = rings[0]
    np.testing.assert_allclose(ring[0], ring[-1])
    np.testing.assert_allclose(np.hypot(ring[:, 0], ring[:, 1]), 300.0, atol=0.5)
    assert signed_area(ring) == pytest.approx(math.pi * 300.0**2, rel=0.01)  # outer ring CCW


def test_hole_in_safe_region_is_a_clockwise_ring():
    radius, origin, res = centred_radius()
    rings = sorted(region_contours(50.0 - np.abs(radius - 200.0), origin, res, 0.0), key=signed_area)
    assert len(rings) == 2
    assert signed_area(rings[0]) == pytest.approx(-math.pi * 150.0**2, rel=0.02)  # hole
    assert signed_area(rings[1]) == pytest.approx(math.pi * 250.0**2, rel=0.02)


def test_unreachable_and_unsafe_cells_are_outside_every_region():
    radius, origin, res = centred_radius(n=21)
    margin = 80.0 - radius
    margin[10, 10] = np.nan  # an unreachable cell punches a hole at the centre
    rings = region_contours(margin, origin, res, 0.0)
    assert sorted(np.sign([signed_area(r) for r in rings])) == [-1.0, 1.0]
