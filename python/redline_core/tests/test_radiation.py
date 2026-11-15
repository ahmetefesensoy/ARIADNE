"""proje.md §7.3 and the cylindrical-pit golden test (§7.14)."""
import math

import numpy as np
import pytest

from redline_core.radiation import dose_rate_site, f_alpha


def test_open_flat_site_sees_the_full_sky():
    assert f_alpha(np.zeros(72), 1.18) == pytest.approx(1.0)


def test_cylindrical_pit_matches_closed_form():
    # Horizon at 30° in every direction: F = 1 - sin(30°)^(α+1) = 1 - 0.5^2.18.
    assert f_alpha(np.full(72, math.radians(30.0)), 1.18) == pytest.approx(0.7793242509273364, rel=1e-12)


def test_terrain_below_the_horizontal_adds_no_sky():
    assert f_alpha(np.full(72, math.radians(-10.0)), 1.18) == pytest.approx(1.0)


def test_sky_view_is_the_mean_over_azimuths_for_every_cell():
    half = np.r_[np.zeros(36), np.full(36, math.radians(30.0))]
    cube = np.stack([np.zeros(72), half])[None, :, :]  # shape (1, 2, 72)
    np.testing.assert_allclose(f_alpha(cube, 1.18), [[1.0, (1.0 + 0.7793242509273364) / 2]], rtol=1e-12)


@pytest.mark.parametrize(("sky", "dose"), [(0.5, 6.0), (1.0, 10.0), (0.0, 2.0)])
def test_site_dose_mixes_horizon_shielded_and_isotropic_parts(sky, dose):
    assert dose_rate_site(10.0, sky) == pytest.approx(dose, rel=1e-12)
