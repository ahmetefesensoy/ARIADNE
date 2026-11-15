"""Habitat siting: pad slope limits, regional plane slope, reach maximisation (D010)."""
import numpy as np
import pytest

from core_helpers import terrain_grid
from redline_core.cost_human import UNOBSERVED, WalkModel, prepare_terrain
from redline_core.siting import SitingRules, pad_mask, regional_slope_deg, select_habitat


def test_regional_slope_of_a_tilted_plane():
    y, x = np.mgrid[0:60, 0:60] * 4.0
    z = np.tan(np.radians(3.0)) * x
    slope = regional_slope_deg(z, 4.0, 100.0)
    np.testing.assert_allclose(slope[10:50, 10:50], 3.0, atol=1e-6)


def test_pad_needs_every_cell_inside_the_limits():
    grid = terrain_grid(np.zeros((20, 20)), 4.0, state=UNOBSERVED, slope_deg=5.0, sigma_deg=1.0)
    grid.layers["slope_deg"][10, 10] = 14.0  # 14 + 1.645·1 > 15: fails the local limit
    terrain = prepare_terrain(grid, WalkModel())
    mask = pad_mask(terrain, grid.layers["slope_deg"], grid.layers["slope_sigma_deg"],
                    SitingRules(pad_cells=3, regional_window_m=40.0))
    assert not mask[9:12, 9:12].any() and mask[5, 5]
    assert not mask[0, :].any()  # pads cannot hang over the grid edge
    unknown = grid.layers["slope_sigma_deg"].copy()
    unknown[5, 5] = np.nan
    assert not pad_mask(terrain, grid.layers["slope_deg"], unknown, SitingRules(pad_cells=3))[5, 5]


def test_regional_limit_rejects_a_steep_flank():
    y, x = np.mgrid[0:40, 0:40] * 4.0
    z = np.tan(np.radians(8.0)) * x  # 8° plane: walkable, but too steep regionally
    grid = terrain_grid(z, 4.0, state=UNOBSERVED, slope_deg=8.0)
    terrain = prepare_terrain(grid, WalkModel())
    assert not pad_mask(terrain, grid.layers["slope_deg"], grid.layers["slope_sigma_deg"],
                        SitingRules(pad_cells=3, regional_window_m=60.0)).any()


def test_selection_prefers_the_pad_with_the_largest_reach():
    grid = terrain_grid(np.zeros((40, 60)), 4.0, state=UNOBSERVED)
    grid.layers["slope_deg"][:, 30] = 40.0   # a wall with one gap: the east part is a dead end
    grid.layers["slope_deg"][20, 30] = 0.0
    grid.layers["slope_deg"][:, 50:] = 40.0
    terrain = prepare_terrain(grid, WalkModel())
    rules = SitingRules(pad_cells=3, regional_window_m=40.0, search_radius_m=200.0, lattice_m=8.0,
                        reach_budget_s=150.0)  # ~17 cells: wider than the 19-column east pocket
    result = select_habitat(terrain, grid.layers["slope_deg"], grid.layers["slope_sigma_deg"], (20, 40), rules)
    assert result.candidates_evaluated > 10 and result.reach_cells > 0
    # The west field is larger, so the best pad lies west of the wall.
    assert result.cell[1] < 30
    assert result.ranking[0]["reach_cells"] == result.reach_cells


def test_selection_fails_loudly_without_candidates():
    grid = terrain_grid(np.zeros((10, 10)), 4.0, slope_deg=20.0, sigma_deg=2.0)
    terrain = prepare_terrain(grid, WalkModel())
    with pytest.raises(ValueError, match="pad"):
        select_habitat(terrain, grid.layers["slope_deg"], grid.layers["slope_sigma_deg"], (5, 5),
                       SitingRules(pad_cells=3, regional_window_m=20.0))
