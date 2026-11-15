"""Known metric fixtures, not archived NASA measurements."""
import math

import pytest

np = pytest.importorskip("numpy", reason="install redline-data[data] for terrain tests")

from redline_data.derive import roughness, sigma, slopes


def plane(shape=(15, 17), resolution=1):
    y, x = np.indices(shape)
    return -4200 + 0.2 * x * resolution - 0.3 * y * resolution


def test_multibaseline_plane_slope_uses_physical_metres():
    dem = plane()
    expected = math.degrees(math.atan(math.hypot(0.2, 0.3)))
    outputs = slopes(dem, 1)
    assert set(outputs) == {2, 5}
    for baseline, values in outputs.items():
        reach = math.ceil(baseline / 2)
        np.testing.assert_allclose(values[reach:-reach, reach:-reach], expected, atol=1e-10)
        assert np.isnan(values[:reach]).all()
        assert np.isnan(values[-reach:]).all()
        assert np.isnan(values[:, :reach]).all()
        assert np.isnan(values[:, -reach:]).all()


def test_slope_on_nonunit_resolution_and_unsigned_dem():
    y, x = np.indices((9, 11))
    values = slopes((4 * x + 2 * y).astype(np.uint16), 2, (4,))[4]
    np.testing.assert_allclose(values[1:-1, 1:-1], math.degrees(math.atan(math.sqrt(5))))


def test_fractional_endpoint_linear_interpolation_retains_requested_baseline():
    # x^3 at +/-2.5 samples is interpolated from the actual +/-2 and +/-3 nodes:
    # (17.5 - -17.5) / 5 = 7, rather than rounding to a 4 m or 6 m span.
    y, x = np.indices((9, 9))
    dem = (x - 4).astype(float) ** 3
    assert slopes(dem, 1, (5,))[5][4, 4] == pytest.approx(math.degrees(math.atan(7)))


@pytest.mark.parametrize("missing", [np.nan, np.inf, -np.inf])
def test_slope_invalidates_full_cross_and_does_not_bridge_missing_interior(missing):
    dem = plane()
    dem[7, 8] = missing
    output = slopes(dem, 1, (5,))[5]
    assert np.isnan(output[7, 8])
    assert np.isnan(output[7, 6])  # missing cell between centre and outer sample
    assert np.isnan(output[5, 8])
    assert np.isfinite(output[5, 6])  # outside the invalid cell's cross support


def test_slope_respects_numpy_mask_without_mutating_input():
    dem = np.ma.array(plane(), mask=False)
    dem.mask[7, 8] = True
    before = dem.copy()
    assert np.isnan(slopes(dem, 1, (2,))[2][7, 7])
    np.testing.assert_array_equal(dem.data, before.data)
    np.testing.assert_array_equal(dem.mask, before.mask)


@pytest.mark.parametrize("baseline", [0, -1, float("nan"), float("inf"), True, 1.5])
def test_unsupported_baseline_is_rejected(baseline):
    with pytest.raises(ValueError):
        slopes(plane(), 1, (baseline,))


def test_source_resolution_cannot_be_claimed_from_planning_grid():
    with pytest.raises(ValueError, match="twice"):
        slopes(plane(), 4, (2, 5))


@pytest.mark.parametrize("baselines", [(), (2, 2), (40,)])
def test_empty_duplicate_or_too_large_support_is_rejected(baselines):
    with pytest.raises(ValueError):
        slopes(plane(), 1, baselines)


@pytest.mark.parametrize("resolution", [0, -1, True, float("nan"), float("inf")])
def test_invalid_resolution_is_rejected(resolution):
    with pytest.raises(ValueError):
        slopes(plane(), resolution)


def test_roughness_of_tilted_plane_is_zero_and_keeps_edges_unknown():
    result = roughness(plane(), 1, radius_m=2)
    np.testing.assert_allclose(result[2:-2, 2:-2], 0, atol=1e-7)
    assert np.isnan(result[:2]).all()
    assert np.isnan(result[:, :2]).all()


def test_roughness_matches_independent_least_squares_plane_fit():
    values = plane((9, 9))
    values[4, 4] += 2
    yy, xx = np.indices((5, 5))
    design = np.column_stack((np.ones(25), xx.ravel(), yy.ravel()))
    observed = values[2:7, 2:7].ravel()
    coefficients, *_ = np.linalg.lstsq(design, observed, rcond=None)
    expected = np.sqrt(np.mean((observed - design @ coefficients) ** 2))
    assert roughness(values, 1, radius_m=2)[4, 4] == pytest.approx(expected)


def test_roughness_invalidates_missing_square_support_and_keeps_other_cells():
    values = np.ma.array(plane(), mask=False)
    values.mask[7, 8] = True
    result = roughness(values, 1, radius_m=2)
    assert np.isnan(result[5:10, 6:11]).all()
    assert np.isfinite(result[3, 3])


@pytest.mark.parametrize("radius", [0, -1, 0.5, 1.5, 30, float("nan")])
def test_roughness_rejects_unsupported_radius(radius):
    with pytest.raises(ValueError):
        roughness(plane(), 1, radius_m=radius)


def test_sigma_removes_only_median_vertical_bias_and_reports_residual_proxy():
    reference = np.zeros((3, 3))
    residual = np.array([[-2, -1, 0], [-1, 0, 1], [0, 1, 2]], dtype=float)
    result = sigma(reference + 12 + residual, reference, alignment_verified=True)
    assert result["vertical_offset_removed_m"] == 12
    np.testing.assert_array_equal(result["residual_m"], residual)
    np.testing.assert_array_equal(result["sigma_proxy_m"], np.abs(residual))
    assert result["rmse_residual_m"] == pytest.approx(np.sqrt(np.mean(residual**2)))
    assert result["median_absolute_residual_m"] == 1
    assert result["overlap_cells"] == 9
    assert "not independent one-sigma" in result["interpretation"]
    assert result["unit"] == "m"


def test_sigma_masked_cells_are_not_filled_with_zero_or_used_for_offset():
    values = np.ma.array(np.full((3, 3), 5.0), mask=False)
    values.mask[0, 0] = True
    reference = np.zeros((3, 3))
    reference[1, 1] = np.nan
    result = sigma(values, reference, alignment_verified=True)
    assert result["overlap_cells"] == 7
    assert result["vertical_offset_removed_m"] == 5
    assert np.isnan(result["residual_m"][0, 0])
    assert np.isnan(result["residual_m"][1, 1])
    assert np.isnan(result["sigma_proxy_m"][0, 0])


def test_sigma_never_invents_second_dtm_or_alignment():
    with pytest.raises(ValueError, match="second DTM"):
        sigma(plane())
    with pytest.raises(ValueError, match="alignment"):
        sigma(plane(), plane())
    with pytest.raises(ValueError, match="identical shapes"):
        sigma(plane(), np.zeros((3, 3)), alignment_verified=True)


def test_sigma_requires_overlap_evidence():
    reference = np.full((3, 3), np.nan)
    reference[0, :2] = 0
    with pytest.raises(ValueError, match="three common"):
        sigma(np.zeros((3, 3)), reference, alignment_verified=True)


@pytest.mark.parametrize("bad", [np.zeros(9), np.zeros((2, 2)), np.ones((3, 3), dtype=complex)])
def test_array_contract_rejects_wrong_shape_or_complex_elevations(bad):
    with pytest.raises(ValueError):
        slopes(bad, 1, (2,))
