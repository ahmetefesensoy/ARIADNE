"""Planning-grid layers and the portable npz + sidecar form (D008, D009)."""
import json

import numpy as np
import pytest

from core_helpers import terrain_grid
from redline_core.cost_human import UNOBSERVED
from redline_core.planning import STORED_LAYERS, build_planning_layers, load_planning_grid, save_planning_grid
from redline_core.walkback import nearest_in_largest_component


def test_build_layers_follow_d008_block_rules():
    fine = np.arange(64, dtype=float).reshape(8, 8)
    sigma = np.ones((8, 8))
    sigma[0, 0] = np.nan  # one missing fine value keeps its block missing
    layers = build_planning_layers(np.zeros((2, 2)), fine * 0.0 + np.add.outer(np.arange(8), np.arange(8)),
                                   fine, fine, sigma, 4, 1.0)
    assert layers["slope_deg"][0, 0] == pytest.approx(fine[:4, :4].mean())
    assert layers["wall_slope_deg"][1, 1] == fine[4:, 4:].max()
    assert np.isnan(layers["slope_sigma_deg"][0, 0]) and layers["slope_sigma_deg"][1, 1] == 1.0
    # A uniform plane has zero detrended relief.
    np.testing.assert_allclose(layers["relief_m"], 0.0, atol=1e-9)


def test_build_layers_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        build_planning_layers(np.zeros((2, 2)), np.zeros((8, 8)), np.zeros((8, 8)), np.zeros((8, 7)),
                              np.zeros((8, 8)), 4, 1.0)


def test_round_trip_preserves_layers_geometry_and_provenance(tmp_path):
    rng = np.random.default_rng(1)
    grid = terrain_grid(rng.normal(size=(5, 7)), 4.0, origin_xy=(-14.0, -10.0), sigma_deg=0.5)
    grid.layers["slope_sigma_deg"][2, 3] = np.nan
    sidecar = save_planning_grid(tmp_path / "plan", grid, {"status": "DERIVED", "inputs": {"a": "b"}})
    loaded, meta = load_planning_grid(tmp_path / "plan.npz")
    assert meta == sidecar and meta["provenance"]["status"] == "DERIVED"
    assert loaded.origin_xy == (-14.0, -10.0) and loaded.resolution_m == 4.0
    assert (loaded.height, loaded.width) == (5, 7)
    for name in STORED_LAYERS:
        np.testing.assert_allclose(loaded.layers[name], np.float32(grid.layers[name]), equal_nan=True)
    assert (loaded.layers["state"] == UNOBSERVED).all()


def test_load_rejects_a_modified_npz(tmp_path):
    grid = terrain_grid(np.zeros((3, 3)))
    save_planning_grid(tmp_path / "plan", grid, {"status": "DERIVED"})
    data = bytearray((tmp_path / "plan.npz").read_bytes())
    data[-1] ^= 0xFF
    (tmp_path / "plan.npz").write_bytes(bytes(data))
    with pytest.raises(ValueError, match="SHA-256"):
        load_planning_grid(tmp_path / "plan.json")


def test_save_refuses_overwrite_and_missing_status(tmp_path):
    grid = terrain_grid(np.zeros((3, 3)))
    with pytest.raises(ValueError):
        save_planning_grid(tmp_path / "a", grid, {"note": "no status"})
    save_planning_grid(tmp_path / "b", grid, {"status": "DERIVED"})
    with pytest.raises(FileExistsError):
        save_planning_grid(tmp_path / "b", grid, {"status": "DERIVED"})


def test_load_rejects_unknown_schema(tmp_path):
    grid = terrain_grid(np.zeros((3, 3)))
    save_planning_grid(tmp_path / "c", grid, {"status": "DERIVED"})
    meta = json.loads((tmp_path / "c.json").read_text())
    meta["schema"] = "other"
    (tmp_path / "c.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="schema"):
        load_planning_grid(tmp_path / "c.npz")


def test_habitat_rule_picks_nearest_cell_of_the_largest_component():
    labels = np.array([
        [0, 0, -1, 1, 1],
        [-1, -1, -1, 1, 1],
        [2, -1, -1, 1, 1],
    ])
    cell, report = nearest_in_largest_component(labels, (0, 0))
    assert cell == (0, 3)
    assert report["components"] == 3 and report["largest_cells"] == 6
    assert report["requested_cell_component_cells"] == 2 and report["shift_cells"] == 3.0
    assert nearest_in_largest_component(labels, (1, 4))[0] == (1, 4)
    with pytest.raises(ValueError):
        nearest_in_largest_component(np.full((2, 2), -1), (0, 0))
    with pytest.raises(ValueError):
        nearest_in_largest_component(labels, (5, 0))


def test_stereo_precision_matches_kirk_formula_for_the_bxw_pair():
    from redline_core.planning import slope_floor_deg, stereo_expected_precision_m

    # ESP_019698 (e = 24.1°) and ESP_019988 (e = 14.7°) on opposite sides; GSD 0.291 m; ρ = 0.2 px.
    ep = stereo_expected_precision_m(0.291, 24.1, 14.7, opposite_sides=True)
    hand = 0.2 * 0.291 / (np.tan(np.radians(24.1)) + np.tan(np.radians(14.7)))
    assert ep == pytest.approx(hand, rel=1e-12) and 0.08 < ep < 0.09
    same_side = stereo_expected_precision_m(0.291, 24.1, 14.7, opposite_sides=False)
    assert same_side > 3 * ep
    assert slope_floor_deg(ep, 5.0) == pytest.approx(np.degrees(np.arctan(np.sqrt(2) * ep / 5.0)), rel=1e-12)
    with pytest.raises(ValueError):
        stereo_expected_precision_m(0.3, 10.0, 10.0, opposite_sides=False)


def test_ensemble_sigma_combines_window_rms_and_floor():
    from redline_core.planning import ensemble_slope_layers

    rng = np.random.default_rng(5)
    truth = np.full((40, 40), 10.0)
    noise = 2.0  # independent processing noise per product, per 4 m cell after averaging
    a = np.repeat(np.repeat(truth + rng.normal(0, noise, truth.shape), 4, 0), 4, 1)
    b = np.repeat(np.repeat(truth + rng.normal(0, noise, truth.shape), 4, 0), 4, 1)
    b[:8, :] = np.nan  # reference missing in the south rows
    mu, sigma, info = ensemble_slope_layers(a, b, 4, window_cells=9, floor_deg=1.0)
    centre = sigma[20:30, 15:25]
    # Mean of two products: σ² ≈ (2·2²)/4 + 1² = 3 → σ ≈ 1.73.
    assert np.median(centre) == pytest.approx(np.sqrt(3.0), rel=0.15)
    # Primary only: σ² ≈ (2·2²)/2 + 1 = 5 → σ ≈ 2.24, and μ is the primary value.
    assert np.median(sigma[:2, 15:25]) == pytest.approx(np.sqrt(5.0), rel=0.2)
    np.testing.assert_allclose(mu[:2, :], a[:8:4, ::4])
    assert abs(np.mean(mu[10:, :]) - 10.0) < 0.1
    assert info["both_fraction"] == pytest.approx(0.95) and info["sigma_missing_fraction"] == 0.0


def test_ensemble_never_turns_missing_into_zero_sigma():
    from redline_core.planning import ensemble_slope_layers

    a = np.full((16, 16), 5.0)
    b = np.full((16, 16), np.nan)
    _, sigma, info = ensemble_slope_layers(a, b, 4, window_cells=3, floor_deg=1.0)
    assert np.isnan(sigma).all() and info["sigma_missing_fraction"] == 1.0  # no D anywhere: stays missing


def test_cells_beyond_the_reference_take_the_nearest_local_rms():
    from redline_core.planning import ensemble_slope_layers

    rng = np.random.default_rng(9)
    a = np.repeat(np.repeat(rng.normal(10, 2, (20, 20)), 4, 0), 4, 1)
    b = np.repeat(np.repeat(rng.normal(10, 2, (20, 20)), 4, 0), 4, 1)
    b[:, :24] = np.nan  # the west 6 planning columns have no reference
    _, sigma, info = ensemble_slope_layers(a, b, 4, window_cells=3, floor_deg=0.5)
    assert np.isfinite(sigma).all() and info["rms_filled_from_nearest_cells"] > 0
    assert info["rms_fill_max_distance_cells"] >= 4
    assert sigma[:, :3].min() > 0.5  # filled cells carry processing noise, never just the floor
    with pytest.raises(ValueError):
        ensemble_slope_layers(a, a, 4, window_cells=4, floor_deg=1.0)
