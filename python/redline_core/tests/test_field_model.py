"""walkback_field core: live margins, red/yellow lines, tiles and recompute policy."""
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from core_helpers import V_FLAT, terrain_grid
from redline_core.cost_human import DETECTED, UNOBSERVED, CrewMember, SuitModel, WalkModel
from redline_core.field_model import CrewInput, EvaConfig, ReturnFieldModel, load_eva, place_habitat
from redline_core.fieldtile import decode_tile
from redline_core.redline import LIM_NONE, LIM_O2, Rates, Resources

REPO = Path(__file__).resolve().parents[3]
WALK = WalkModel()
SUIT = SuitModel()
CREW = {"EV1": CrewMember("EV1", 75.0, 80.0), "EV2": CrewMember("EV2", 68.0, 80.0, theta=1.3)}


def eva(**changes) -> EvaConfig:
    base = EvaConfig(site_id="TST", crew_ids=("EV1",), habitat_requested_xy=(2.0, 2.0),
                     reserve=Resources(0.1, 0.0, 0.0, 0.0), start_minutes_above_reserve=30.0,
                     terminate_threshold_min=10.0, sigma_fallback_percentile=95.0, tile_lo_min=-60.0,
                     tile_hi_min=60.0, tile_bit_depth=8, line_tolerance_m=0.0)
    return replace(base, **changes)


def flat(shape=(20, 40), state=UNOBSERVED, **kwargs):
    return terrain_grid(np.zeros(shape), 4.0, state=state, **kwargs)


def start_input(model, crew_id="EV1", xy=None):
    return CrewInput(model.start_resources(crew_id), model.nominal_rates(crew_id), xy)


def test_repo_eva_config_loads():
    config = load_eva(REPO / "config" / "eva.yaml")
    assert config.site_id == "BXW" and config.crew_ids == ("EV1",)
    assert config.reserve.o2_kg == 0.1 and config.tile_bit_depth == 8


def test_eva_config_rejects_unknown_keys(tmp_path):
    text = (REPO / "config" / "eva.yaml").read_text(encoding="utf-8") + "\nsurprise: 1\n"
    (tmp_path / "eva.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="unknown"):
        load_eva(tmp_path / "eva.yaml")


def test_margin_at_habitat_equals_start_minutes_and_falls_with_distance():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva())
    assert model.habitat_cell == (0, 0)
    snap = model.snapshot({"EV1": start_input(model, xy=model.habitat_xy)})
    assert snap.margin_now_min == pytest.approx(30.0)
    assert snap.limiting_crew_id == "EV1" and snap.limiting_consumable == LIM_O2
    far = model.snapshot({"EV1": start_input(model, xy=(150.0, 2.0))})
    # Unobserved flat ground: 148 m at 0.7·v(0); the risk factor makes the need larger.
    walk_min = 148.0 / (WALK.speed_factor_unobserved * V_FLAT) / 60.0
    assert far.margin_now_min < 30.0 - walk_min


SHORT = dict(start_minutes_above_reserve=2.0, terminate_threshold_min=1.0)  # the line crosses an 80×160 m grid


def test_abort_ring_bounds_the_reachable_region_and_terminate_is_inside_it():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(**SHORT))
    snap = model.snapshot({"EV1": start_input(model)})
    margin = snap.combined.field.margin_s
    assert (margin[0, 0] > 0) and (margin[:, -1] < 0).all()  # the line crosses the grid

    def area(rings):
        return sum(0.5 * float(np.sum(r[:, 0] * np.roll(r[:, 1], -1) - np.roll(r[:, 0], -1) * r[:, 1]))
                   for r in rings)

    safe_cells = np.count_nonzero(margin >= 0.0) * 16.0
    assert area(snap.abort_rings) == pytest.approx(safe_cells, rel=0.15)
    assert 0 < area(snap.terminate_rings) < area(snap.abort_rings)
    assert all(r.shape[1] == 3 for r in snap.abort_rings)
    np.testing.assert_allclose(snap.abort_rings[0][:, 2], 0.0)  # z from the DEM (flat at 0)


def test_simplification_reduces_vertices_and_keeps_closed_rings():
    plain = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(**SHORT))
    raw = plain.snapshot({"EV1": start_input(plain)})
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(line_tolerance_m=2.0, **SHORT))
    simple = model.snapshot({"EV1": start_input(model)})
    assert sum(len(r) for r in simple.abort_rings) < sum(len(r) for r in raw.abort_rings)
    assert all(np.array_equal(r[0], r[-1]) for r in simple.abort_rings)


def test_small_holes_are_dropped_from_display_rings_only():
    grid = flat((30, 30))
    grid.layers["slope_deg"][10, 10] = 40.0  # one banned cell: a 16 m² hole in the safe region
    keep = ReturnFieldModel(grid, WALK, SUIT, CREW, eva())
    drop = ReturnFieldModel(grid, WALK, SUIT, CREW, eva(min_hole_area_m2=100.0))
    a, b = keep.snapshot({"EV1": start_input(keep)}), drop.snapshot({"EV1": start_input(drop)})
    assert len(a.abort_rings) == 2 and len(b.abort_rings) == 1
    assert np.isnan(b.combined.field.margin_s[10, 10])  # the field itself is unchanged


def test_no_position_gives_nan_now_and_no_limiting_crew():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva())
    snap = model.snapshot({"EV1": start_input(model)})
    assert math.isnan(snap.margin_now_min) and snap.limiting_crew_id == ""
    assert snap.limiting_consumable == LIM_NONE
    outside = model.snapshot({"EV1": start_input(model, xy=(-50.0, 0.0))})
    assert math.isnan(outside.margin_now_min)


def test_unreachable_position_is_nan_and_counts_as_the_worst_crew():
    z = np.zeros((10, 30))
    grid = terrain_grid(z, 4.0, state=UNOBSERVED)
    grid.layers["slope_deg"][:, 20] = 40.0  # a wall column cuts the grid; the west part is larger
    model = ReturnFieldModel(grid, WALK, SUIT, CREW, eva(crew_ids=("EV1", "EV2")))
    snap = model.snapshot({"EV1": start_input(model, xy=(10.0, 10.0)),
                           "EV2": start_input(model, "EV2", xy=(100.0, 10.0))})
    assert math.isfinite(snap.crews["EV1"].now_min) and math.isnan(snap.crews["EV2"].now_min)
    assert snap.limiting_crew_id == "EV2" and math.isnan(snap.margin_now_min)
    assert snap.limiting_consumable == LIM_NONE


def test_two_crew_line_follows_the_worse_member():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(crew_ids=("EV1", "EV2")))
    ev1 = start_input(model, xy=(30.0, 2.0))
    ev2 = CrewInput(model.start_resources("EV2"), model.nominal_rates("EV2"), (30.0, 2.0))
    half = CrewInput(Resources(0.1 + (ev2.remaining.o2_kg - 0.1) / 2, ev2.remaining.co2_capacity_kg / 2,
                               ev2.remaining.water_kg / 2, ev2.remaining.battery_wh / 2), ev2.rates, ev2.xy)
    snap = model.snapshot({"EV1": ev1, "EV2": half})
    np.testing.assert_array_equal(snap.combined.field.margin_s,
                                  np.fmin(snap.crews["EV1"].margin.margin_s, snap.crews["EV2"].margin.margin_s))
    assert snap.limiting_crew_id == "EV2" and snap.margin_now_min == pytest.approx(snap.crews["EV2"].now_min)


def test_lower_remaining_shrinks_the_line_without_a_new_dijkstra():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(**SHORT))
    full = model.snapshot({"EV1": start_input(model)})
    item = start_input(model)
    low = CrewInput(Resources(0.1 + (item.remaining.o2_kg - 0.1) / 2, item.remaining.co2_capacity_kg / 2,
                              item.remaining.water_kg / 2, item.remaining.battery_wh / 2), item.rates, None)
    later = model.snapshot({"EV1": low})
    assert later.field_version == full.field_version == 1
    assert np.count_nonzero(later.combined.field.margin_s >= 0) < np.count_nonzero(full.combined.field.margin_s >= 0)


def test_cell_states_mark_dirty_and_observed_ground_widens_the_line():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(**SHORT))
    before = model.snapshot({"EV1": start_input(model)})
    cells = [(iy, ix, DETECTED) for iy in range(20) for ix in range(40)]
    assert model.apply_states(cells) == 800 and model.dirty
    assert model.apply_states(cells) == 0
    after = model.snapshot({"EV1": start_input(model)})
    assert after.field_version == 2 and not model.dirty
    assert np.count_nonzero(after.combined.field.margin_s >= 0) > np.count_nonzero(before.combined.field.margin_s >= 0)
    with pytest.raises(ValueError):
        model.apply_states([(0, 0, 9)])
    with pytest.raises(ValueError):
        model.apply_states([(99, 0, DETECTED)])


def test_habitat_moves_into_the_largest_component():
    grid = flat((10, 30))
    grid.layers["slope_deg"][:, 3] = 40.0  # (0,0) is in a 3-column pocket
    model = ReturnFieldModel(grid, WALK, SUIT, CREW, eva())
    assert model.habitat_cell == (0, 4) and model.habitat_report["shift_cells"] == 4.0


def test_missing_sigma_uses_the_percentile_fallback_never_zero():
    grid = flat((10, 10), sigma_deg=2.0)
    grid.layers["slope_sigma_deg"][5, 5] = np.nan
    model = ReturnFieldModel(grid, WALK, SUIT, CREW, eva())
    assert model.sigma_fallback_deg == pytest.approx(2.0)
    assert ReturnFieldModel(flat((10, 10)), WALK, SUIT, CREW, eva()).sigma_fallback_deg is None


def test_tile_decodes_to_the_margin_within_one_step():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva())
    snap = model.snapshot({"EV1": start_input(model)})
    margin_min = snap.combined.field.margin_min
    tile = model.tile(margin_min)
    decoded = decode_tile(tile.png, tile.scale, tile.offset, tile.nodata_byte)
    expected = np.clip(margin_min, -60.0, 60.0)
    assert np.nanmax(np.abs(decoded - expected)) <= tile.scale / 2 + 1e-6
    assert np.array_equal(np.isnan(decoded), np.isnan(margin_min))


def test_rejects_unknown_crew_and_empty_inputs():
    with pytest.raises(ValueError):
        ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(crew_ids=("EV9",)))
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva())
    with pytest.raises(ValueError):
        model.snapshot({})
    with pytest.raises(ValueError):
        model.snapshot({"EV2": start_input(model)})


def test_rates_change_minutes_but_not_the_zero_line():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva())
    item = start_input(model, xy=(40.0, 2.0))
    fast = CrewInput(item.remaining, Rates(item.rates.o2_kg_s * 2, item.rates.co2_kg_s * 2,
                                           item.rates.water_kg_s * 2, item.rates.battery_w * 2), item.xy)
    a, b = model.snapshot({"EV1": item}), model.snapshot({"EV1": fast})
    assert b.margin_now_min == pytest.approx(a.margin_now_min / 2, rel=1e-9)
    np.testing.assert_array_equal(a.combined.field.margin_s >= 0, b.combined.field.margin_s >= 0)


def test_design_point_start_and_time_based_reserve():
    from redline_core.cost_human import consumables_from_energy
    from redline_core.field_model import reserve_resources, start_resources

    config = eva(start_basis="design_point", design_duration_h=8.0, design_metabolic_w=351.7,
                 reserve_minutes=30.0)
    per_s = consumables_from_energy(351.7, 1.0, SUIT)  # design consumption per second
    reserve = reserve_resources(SUIT, config)
    assert reserve.o2_kg == pytest.approx(max(0.1, per_s.o2_kg * 1800.0))  # FR-01 floor kept
    assert reserve.water_kg == pytest.approx(per_s.water_kg * 1800.0)
    assert reserve.battery_wh == pytest.approx(per_s.battery_wh * 1800.0)
    start = start_resources(CREW["EV1"], SUIT, WALK, config)
    assert start.water_kg == pytest.approx(reserve.water_kg + per_s.water_kg * 8 * 3600.0)
    assert start.o2_kg == pytest.approx(reserve.o2_kg + per_s.o2_kg * 8 * 3600.0)
    # The suit is sized for the design point, so it is the same for every crew member.
    assert start_resources(CREW["EV2"], SUIT, WALK, config) == start


def test_fixed_habitat_uses_the_selected_cell_and_rejects_banned_ones():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(habitat_requested_xy=(42.0, 22.0),
                                                           habitat_placement="fixed"))
    assert model.habitat_cell == (5, 10) and model.habitat_report["in_largest_component"]
    grid = flat()
    grid.layers["slope_deg"][5, 10] = 40.0
    with pytest.raises(ValueError, match="not walkable"):
        ReturnFieldModel(grid, WALK, SUIT, CREW, eva(habitat_requested_xy=(42.0, 22.0), habitat_placement="fixed"))


def test_vertex_budget_coarsens_tolerance_and_quantum_rounds_vertices():
    plain = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(**SHORT))
    base = plain.snapshot({"EV1": start_input(plain)})
    total = sum(len(r) for r in base.abort_rings + base.terminate_rings)
    tight = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva(max_display_vertices=max(total // 3, 8),
                                                            display_quantum_m=0.0625, **SHORT))
    snap = tight.snapshot({"EV1": start_input(tight)})
    assert snap.line_tolerance_m > base.line_tolerance_m
    assert sum(len(r) for r in snap.abort_rings + snap.terminate_rings) <= max(total // 3, 8) or         snap.line_tolerance_m == tight.eva.max_line_tolerance_m
    for ring in snap.abort_rings:
        np.testing.assert_array_equal(ring * 16, np.round(ring * 16))
        assert np.array_equal(ring[0], ring[-1])


def test_sep_mode_limits_the_line_to_the_shelter_walk_and_marks_shelter():
    from redline_core.redline import LIM_SHELTER

    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva())
    normal = model.snapshot({"EV1": start_input(model, xy=(150.0, 2.0))})
    sep = model.snapshot({"EV1": start_input(model, xy=(150.0, 2.0))}, shelter_max_s=120.0)
    w_eps = model.field.time_eps_s(model.eva.z_eps, model.eva.sigma_theta)
    margin = sep.combined.field.margin_s
    assert np.all(np.isneginf(margin[w_eps > 120.0]))
    assert np.all(sep.combined.field.limiting[w_eps > 120.0] == LIM_SHELTER)
    assert np.count_nonzero(margin >= 0) < np.count_nonzero(normal.combined.field.margin_s >= 0)
    assert np.isneginf(sep.margin_now_min) and sep.limiting_consumable == LIM_SHELTER


def test_daylight_budget_limits_margins_and_names_daylight():
    from redline_core.redline import LIM_DAYLIGHT

    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva())
    item = start_input(model, xy=(42.0, 2.0))
    free = model.snapshot({"EV1": item})
    dusk = model.snapshot({"EV1": item}, daylight_budget_s=120.0)  # 2 min before the dusk limit
    w_eps = model.field.time_eps_s(model.eva.z_eps, model.eva.sigma_theta)
    np.testing.assert_allclose(dusk.combined.field.margin_s, np.minimum(free.combined.field.margin_s, 120.0 - w_eps))
    assert dusk.limiting_consumable == LIM_DAYLIGHT and dusk.margin_now_min < 2.0


def test_place_habitat_alone_matches_the_model_for_both_placements():
    grid = flat((10, 30), sigma_deg=2.0)
    grid.layers["slope_deg"][:, 3] = 40.0  # pocket around (0,0): nearest placement shifts
    grid.layers["slope_sigma_deg"][7, 20] = np.nan  # σ fallback path is shared too
    for config in (eva(), eva(habitat_requested_xy=(42.0, 22.0), habitat_placement="fixed")):
        model = ReturnFieldModel(grid, WALK, SUIT, CREW, config)
        placement = place_habitat(grid, WALK, config)
        assert placement.cell == model.habitat_cell and placement.xy == model.habitat_xy
        assert placement.report == model.habitat_report
    assert place_habitat(grid, WALK, eva()).cell == (0, 4)


def test_blocked_cells_are_banned_and_a_blocked_wall_cuts_the_far_side_off():
    grid = flat((10, 30))
    model = ReturnFieldModel(grid, WALK, SUIT, CREW, eva())
    far = (0, 20)
    assert math.isfinite(model.field.time_s[far])
    wall = [(iy, 10, DETECTED, True) for iy in range(10)]  # full column at ix = 10
    assert model.apply_updates(wall) == 10 and model.dirty
    model.recompute()
    assert math.isinf(model.field.time_s[far]) and math.isinf(model.field.time_s[(4, 10)])
    # A passable update over a blocked cell leaves it blocked (D015: blocked wins).
    model.apply_updates([(4, 10, DETECTED, False)])
    model.recompute()
    assert math.isinf(model.field.time_s[far])


def test_leak_factor_is_one_nominally_and_the_o2_rate_ratio_under_a_leak():
    from redline_core.field_model import leak_factor
    power = 300.0
    o2 = Rates.from_metabolic_power(power, SUIT).o2_kg_s
    assert leak_factor(o2, power, SUIT) == pytest.approx(1.0)
    assert leak_factor(3.0 * o2, power, SUIT) == pytest.approx(3.0)
    assert leak_factor(0.5 * o2, power, SUIT) == 1.0  # never makes the need smaller than the model's
    with pytest.raises(ValueError):
        leak_factor(math.nan, power, SUIT)


def test_a_leak_scales_the_o2_needed_to_walk_back_not_only_the_rate():
    model = ReturnFieldModel(flat(), WALK, SUIT, CREW, eva())
    nominal = model.nominal_rates("EV1")
    leak = Rates(3.0 * nominal.o2_kg_s, nominal.co2_kg_s, nominal.water_kg_s, nominal.battery_w)
    start = model.start_resources("EV1")
    plenty = Resources(start.o2_kg, 1e3, 1e3, 1e6)  # only O2 can limit
    need = model.field.consumables(CREW["EV1"], SUIT, WALK, risk=True, z=model.eva.z_eps,
                                   sigma_theta=model.eva.sigma_theta).o2_kg
    cell = (5, 30)
    available = plenty.o2_kg - model.reserve.o2_kg
    expected = (available - 3.0 * need[cell]) / leak.o2_kg_s  # hand: (R − R_rez − k·W) / (k·ṙ)
    field = model.crew_margin("EV1", plenty, leak, o2_need_factor=3.0)
    assert field.margin_s[cell] == pytest.approx(expected, rel=1e-9)
    optimistic = model.crew_margin("EV1", plenty, leak)
    assert optimistic.margin_s[cell] == pytest.approx((available - need[cell]) / leak.o2_kg_s, rel=1e-9)
    xy = model.grid.cell_center(*cell)
    snap = model.snapshot({"EV1": CrewInput(plenty, leak, xy, o2_need_factor=3.0)})
    assert snap.margin_now_min == pytest.approx(expected / 60.0, rel=1e-6)
