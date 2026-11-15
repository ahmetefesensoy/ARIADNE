"""Terrain line of sight on the planning DTM (FR-05, D015). Expected values by hand."""
import numpy as np
import pytest

from redline_core.los import sight_clearance

R = 4.0
ORIGIN = (0.0, 0.0)  # cell (iy, ix) centre = (4·ix + 2, 4·iy + 2)


def dtm(shape=(10, 40)):
    return np.zeros(shape)


def test_flat_ground_is_visible_with_the_lower_eye_height_as_clearance():
    assert sight_clearance(dtm(), ORIGIN, R, (2.0, 18.0), (150.0, 18.0), 2.0, 2.0) == pytest.approx(2.0)


def test_a_ridge_between_blocks_and_clearance_is_symmetric():
    z = dtm()
    z[:, 18] = 5.0  # column centred at x = 74 m
    a, b = (2.0, 18.0), (150.0, 18.0)
    c = sight_clearance(z, ORIGIN, R, a, b, 2.0, 2.0)
    assert c == pytest.approx(2.0 - 5.0)  # line at 2 m, ridge 5 m → 3 m below
    assert sight_clearance(z, ORIGIN, R, b, a, 2.0, 2.0) == pytest.approx(c)


def test_spec_heights_decide_a_low_ridge():
    z = dtm()
    z[:, 18] = 2.6  # midway between x = 2 and x = 146
    a, b = (2.0, 18.0), (146.0, 18.0)
    assert sight_clearance(z, ORIGIN, R, a, b, 2.0, 2.0) == pytest.approx(-0.6)  # EV ↔ EV: hidden
    assert sight_clearance(z, ORIGIN, R, a, b, 3.0, 3.0) == pytest.approx(0.4)  # antenna ↔ antenna: seen
    assert sight_clearance(z, ORIGIN, R, a, b, 2.0, 3.0) == pytest.approx(2.5 - 2.6)  # line 2.5 m at mid


def test_endpoints_outside_the_grid_or_without_terrain_are_rejected():
    z = dtm()
    with pytest.raises(ValueError):
        sight_clearance(z, ORIGIN, R, (2.0, 18.0), (500.0, 18.0), 2.0, 2.0)
    z[4, 10] = np.nan
    with pytest.raises(ValueError):
        sight_clearance(z, ORIGIN, R, (42.0, 18.0), (100.0, 18.0), 2.0, 2.0)
