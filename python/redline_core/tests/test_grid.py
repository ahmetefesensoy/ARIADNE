import math

import numpy as np
import pytest

from redline_core.grid import (
    Grid,
    block_detrended_relief,
    block_reduce,
    edge_grade,
    neighbors16,
    north_up_to_grid,
)


def test_neighbors16_are_the_sixteen_primitive_offsets():
    expected = {
        (0, 1), (0, -1), (1, 0), (-1, 0),
        (1, 1), (1, -1), (-1, 1), (-1, -1),
        (1, 2), (1, -2), (-1, 2), (-1, -2),
        (2, 1), (2, -1), (-2, 1), (-2, -1),
    }
    offsets = neighbors16()
    assert len(offsets) == 16
    assert set(offsets) == expected


def test_edge_grade_is_signed_rise_over_run():
    res = 2.0
    x = (np.arange(5) + 0.5) * res
    z = np.tile(0.1 * x, (5, 1))  # rises toward +x (east)
    assert edge_grade(z, 2, 2, 0, 1, res) == pytest.approx(0.1)
    assert edge_grade(z, 2, 2, 0, -1, res) == pytest.approx(-0.1)
    assert edge_grade(z, 2, 2, 1, 0, res) == pytest.approx(0.0)
    # knight move (dy=1, dx=2): 0.4 m rise over 2·sqrt(5) m
    assert edge_grade(z, 1, 1, 1, 2, res) == pytest.approx(0.4 / (2 * math.sqrt(5)))


def test_grid_rejects_layer_with_wrong_shape():
    with pytest.raises(ValueError, match="shape"):
        Grid((0.0, 0.0), 4.0, width=3, height=2, layers={"z_m": np.zeros((3, 2))})


@pytest.mark.parametrize("resolution", [0.0, -1.0, math.nan, math.inf])
def test_grid_rejects_invalid_resolution(resolution):
    with pytest.raises(ValueError):
        Grid((0.0, 0.0), resolution, width=1, height=1, layers={})


def test_cell_centre_and_index_use_south_west_origin():
    grid = Grid((-10.0, -20.0), 4.0, width=5, height=3, layers={})
    assert grid.cell_center(0, 0) == (-8.0, -18.0)
    assert grid.cell_center(2, 3) == (4.0, -10.0)
    assert grid.cell_index(4.1, -9.9) == (2, 3)
    with pytest.raises(ValueError):
        grid.cell_index(-10.1, 0.0)
    with pytest.raises(ValueError):
        grid.cell_index(0.0, -7.9)  # top edge is y = -20 + 3·4 = -8


def test_north_up_raster_is_flipped_so_row_zero_is_south():
    raster = np.array([[1, 2], [3, 4]])  # raster row 0 = north
    np.testing.assert_array_equal(north_up_to_grid(raster), [[3, 4], [1, 2]])


def test_block_reduce_mean_and_max():
    a = np.arange(16, dtype=float).reshape(4, 4)
    np.testing.assert_allclose(block_reduce(a, 2, "mean"), [[2.5, 4.5], [10.5, 12.5]])
    np.testing.assert_allclose(block_reduce(a, 2, "max"), [[5.0, 7.0], [13.0, 15.0]])


def test_block_reduce_keeps_missing_values_missing_per_block():
    a = np.ones((4, 4))
    a[0, 0] = np.nan
    for how in ("mean", "max"):
        out = block_reduce(a, 2, how)
        assert np.isnan(out[0, 0])
        np.testing.assert_allclose([out[0, 1], out[1, 0], out[1, 1]], [1.0, 1.0, 1.0])


def test_block_reduce_rejects_shape_not_divisible_by_factor():
    with pytest.raises(ValueError):
        block_reduce(np.zeros((5, 4)), 2, "mean")


def test_detrended_relief_ignores_plane_and_measures_bump():
    yy, xx = np.mgrid[0:4, 0:4].astype(float)
    plane = 0.3 * xx + 0.2 * yy
    np.testing.assert_allclose(block_detrended_relief(plane, 4, 1.0), [[0.0]], atol=1e-12)
    # A centred 2×2 bump has zero first moments, so the fitted plane only gains
    # its mean (0.25 m); residual range is 0.75 - (-0.25) = 1.0 m.
    bump = plane.copy()
    bump[1:3, 1:3] += 1.0
    np.testing.assert_allclose(block_detrended_relief(bump, 4, 1.0), [[1.0]], atol=1e-12)
