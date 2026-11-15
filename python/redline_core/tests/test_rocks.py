"""proje.md §7.4: Golombek rock abundance model (outputs are SCENARIO rocks)."""
import math

import numpy as np
import pytest
from scipy import integrate

from redline_core.rocks import area_fraction_ge, fit_k, n_ge, sample_rocks


def number_density(d, k):
    """Hand derivation: F(D) = k·exp(-qD) is the area fraction of rocks >= D, so the
    number density is n(D) = -F'(D) / (π D² / 4) = k q exp(-qD) / (π D² / 4)."""
    q = 1.79 + 0.152 / k
    return k * q * np.exp(-q * d) / (math.pi * d**2 / 4.0)


@pytest.mark.parametrize(("k", "d"), [(0.02, 0.5), (0.08, 0.3), (0.2, 1.0), (0.3, 0.1)])
def test_closed_form_cumulative_count_matches_numerical_integral(k, d):
    numeric, _ = integrate.quad(number_density, d, np.inf, args=(k,), limit=200)
    assert n_ge(d, k) == pytest.approx(numeric, rel=0.01)


def test_area_fraction_decays_exponentially_from_k():
    assert area_fraction_ge(0.0, 0.05) == pytest.approx(0.05)
    assert area_fraction_ge(1.0, 0.05) == pytest.approx(0.05 * math.exp(-4.83), rel=1e-12)


def test_sampled_count_and_sizes_follow_the_model():
    k, area, d_range = 0.05, 5.0e5, (0.5, 5.0)  # ≈2800 rocks: size fraction σ ≈ 0.005
    rocks = sample_rocks(k, area, d_range, seed=3)
    expected = area * (n_ge(0.5, k) - n_ge(5.0, k))
    assert abs(len(rocks) - expected) < 5.0 * math.sqrt(expected)
    assert rocks.min() >= 0.5 and rocks.max() <= 5.0
    big = (n_ge(1.0, k) - n_ge(5.0, k)) / (n_ge(0.5, k) - n_ge(5.0, k))
    assert np.mean(rocks >= 1.0) == pytest.approx(big, abs=0.03)


def test_sample_rocks_is_reproducible_for_a_seed():
    a = sample_rocks(0.08, 1.0e4, (0.3, 3.0), seed=11)
    b = sample_rocks(0.08, 1.0e4, (0.3, 3.0), seed=11)
    np.testing.assert_array_equal(a, b)


def test_fit_k_recovers_known_abundance():
    area = 2.0e5
    rocks = sample_rocks(0.08, area, (0.3, 3.0), seed=11)
    assert fit_k(rocks, area, 0.3) == pytest.approx(0.08, rel=0.15)


def test_fit_k_stays_within_physical_bounds():
    assert fit_k(np.array([0.31]), 1.0e6, 0.3) == pytest.approx(0.005, abs=1e-4)
    assert fit_k(np.full(400_000, 0.35), 1.0e4, 0.3) == pytest.approx(0.3, abs=1e-4)
