"""Analytical terrain fixtures for bounded relative DEM registration."""
import pytest

np = pytest.importorskip("numpy", reason="install redline-data[data] for registration tests")

from redline_data.registration import register, shift_array


def surface(shape=(100, 110), resolution=1):
    row, col = np.indices(shape)
    x, y = col * resolution, -row * resolution
    return -4300 + 4 * np.sin(x / 7) + 3 * np.cos(y / 11) + 2 * np.sin((x + y) / 9) + .02 * x


def test_shift_array_east_north_convention_and_fractional_interpolation():
    rows, cols = np.indices((10, 12))
    reference = 2.0 * cols - 3.0 * rows
    shifted = shift_array(reference, 1.5, -.5, 1)
    np.testing.assert_allclose(shifted[1:-2, 2:-2], reference[1:-2, 2:-2] - 1.5)
    assert np.isnan(shifted[0]).all()


@pytest.mark.parametrize("dx,dy,bias", [(2.3, -1.6, 6.2), (-2.2, 1.7, -4.1), (0, 0, 3)])
def test_register_recovers_noninteger_translation_and_vertical_bias(dx, dy, bias):
    reference = surface()
    primary = shift_array(reference, dx, dy, 1) + bias
    fit = register(primary, reference, 1, 5, grids_verified=True)
    assert fit["shift_east_m"] == pytest.approx(dx, abs=.025)
    assert fit["shift_north_m"] == pytest.approx(dy, abs=.025)
    assert fit["vertical_offset_removed_m"] == pytest.approx(bias, abs=.01)
    assert fit["converged"]
    assert fit["fit_cells"] + fit["heldout_cells"] <= 12000
    assert fit["heldout_cells"] >= 10
    assert fit["after_heldout"]["rmse_m"] < .01
    assert "not absolute geodetic" in fit["interpretation"]


def test_registration_on_coarser_metric_grid_and_disjoint_holdout():
    reference = surface(resolution=4)
    primary = shift_array(reference, 5.4, -3.2, 4) + 8
    fit = register(primary, reference, 4, 16, grids_verified=True, max_samples=3000)
    assert fit["shift_east_m"] == pytest.approx(5.4, abs=.05)
    assert fit["shift_north_m"] == pytest.approx(-3.2, abs=.05)
    assert fit["fit_cells"] + fit["heldout_cells"] <= 3000
    assert fit["after_heldout"]["rmse_m"] < fit["before_heldout"]["rmse_m"]


def test_masks_remain_unknown_and_missing_regions_not_filled():
    reference = np.ma.array(surface(), mask=False)
    reference.mask[30:35, 40:44] = True
    primary = shift_array(reference, 1.4, .6, 1) + 2
    fit = register(primary, reference, 1, 4, grids_verified=True)
    assert fit["shift_east_m"] == pytest.approx(1.4, abs=.03)
    assert np.isnan(fit["aligned_reference"][31:35, 42:44]).all()


@pytest.mark.parametrize("kind", ["flat", "plane", "one_axis"])
def test_ambiguous_terrain_is_rejected(kind):
    rows, cols = np.indices((80, 90))
    values = np.zeros((80, 90)) if kind == "flat" else 2 * cols + rows
    if kind == "one_axis":
        values = np.sin(cols / 5)
    with pytest.raises(ValueError, match="Degenerate"):
        register(values, values, 1, 5, grids_verified=True)


def test_registration_requires_explicit_metadata_preconditions():
    with pytest.raises(ValueError, match="Verify common"):
        register(surface(), surface(), 1)


def test_shift_budget_and_convergence_are_gates_not_success_labels():
    reference = surface()
    primary = shift_array(reference, 6, -4, 1) + 2
    with pytest.raises(ValueError):
        register(primary, reference, 1, 2, grids_verified=True)
    with pytest.raises(ValueError, match="iteration|convergence"):
        register(primary, reference, 1, 10, grids_verified=True, max_iterations=1)


def test_insufficient_overlap_and_shape_mismatch_rejected():
    reference = np.full((80, 90), np.nan)
    reference[40:43, 40:43] = 1
    with pytest.raises(ValueError, match="Insufficient common"):
        register(surface((80, 90)), reference, 1, 5, grids_verified=True)
    with pytest.raises(ValueError, match="same grid shape"):
        register(surface(), surface((101, 110)), 1, grids_verified=True)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True])
def test_invalid_resolution_rejected(value):
    with pytest.raises(ValueError):
        register(surface(), surface(), value, grids_verified=True)


def test_outliers_do_not_control_translation_fit():
    reference = surface()
    primary = shift_array(reference, 1.9, -2.2, 1) + 4
    primary[25::11, 25::13] += 50
    fit = register(primary, reference, 1, 5, grids_verified=True)
    assert fit["shift_east_m"] == pytest.approx(1.9, abs=.08)
    assert fit["shift_north_m"] == pytest.approx(-2.2, abs=.08)


def test_fixed_objective_converges_with_spatially_varying_residual_amplitude():
    # A changing candidate-specific clipping scale is not a fixed objective:
    # gradients can then stall against an unrelated score. Keep a regression
    # with structured mismatch (not identical translated rasters).
    reference = surface((140, 150), resolution=2)
    primary = shift_array(reference, -3.4, 4.7, 2) - 5
    rows, cols = np.indices(primary.shape)
    primary += .12*np.sin(rows/5)*np.cos(cols/9)
    fit = register(primary, reference, 2, 12, grids_verified=True)
    assert fit["converged"]
    assert fit["shift_east_m"] == pytest.approx(-3.4, abs=.12)
    assert fit["shift_north_m"] == pytest.approx(4.7, abs=.12)
    assert fit["after_heldout"]["rmse_m"] < fit["before_heldout"]["rmse_m"]
