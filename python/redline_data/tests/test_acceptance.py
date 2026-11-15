"""Acceptance thresholds reject incomplete evidence even when other gates pass."""
from copy import deepcopy

import pytest

pytest.importorskip("numpy")
pytest.importorskip("rasterio")
pytest.importorskip("pyproj")
from redline_data.acceptance import evaluate_gates


@pytest.fixture
def evidence():
    qa = {"nodata_fraction": 0, "three_points": [{"absolute_error_m": .0001} for _ in range(3)]}
    return dict(qa_fine=deepcopy(qa), qa_plan=deepcopy(qa),
        vertical={"status": "metadata_verified", "products": {
            "MSL_Gale_DEM_Mosaic_1m_v3": {"vertical_datum": "MOLA", "units": "m"},
            "DTEEC_019698_1750_019988_1750_U01": {"vertical_datum": "Mars 2000 equipotential", "units": "m"}}},
        comparison={"registration": {"converged": True, "max_shift_m_per_axis": 80,
            "shift_east_m": -30, "shift_north_m": 30, "heldout_cells": 2000,
            "before_heldout": {"rmse_m": 6}, "after_heldout": {"rmse_m": 1}},
            "slope_disagreement": {"unit": "degree", "baseline_m": 5},
            "assets": {"slope_sigma": {"nodata_fraction": .03}}},
        stac={"ok": True, "network_retrieval": False, "items_validated": 12},
        tests={"tests": 280, "errors": 0, "failures": 0, "skipped": 0},
        transfer={"passed": True, "predeclared_tolerance_m": .1,
                  "points": [{"abs_residual_m": 1e-6} for _ in range(3)]})


def test_all_t1_data_gates_can_pass_without_claiming_independent_accuracy(evidence):
    gates = evaluate_gates(**evidence)
    assert len(gates) == 8 and all(gates.values())


@pytest.mark.parametrize("kind", ["missing_point", "height_error", "nonfinite", "nodata_at_limit", "negative_nodata"])
def test_three_point_and_nodata_limits_are_enforced(evidence, kind):
    qa = evidence["qa_fine"]
    if kind == "missing_point":
        qa["three_points"].pop()
    elif kind == "height_error":
        qa["three_points"][0]["absolute_error_m"] = .101
    elif kind == "nonfinite":
        qa["three_points"][0]["absolute_error_m"] = float("nan")
    else:
        qa["nodata_fraction"] = .02 if kind == "nodata_at_limit" else -.1
    assert not evaluate_gates(**evidence)["fine_source_transfer_and_nodata"]


@pytest.mark.parametrize("kind", ["not_converged", "boundary", "worse", "missing_holdout", "nonfinite"])
def test_registration_failure_cannot_be_promoted_by_other_green_tests(evidence, kind):
    fit = evidence["comparison"]["registration"]
    if kind == "not_converged":
        fit["converged"] = False
    elif kind == "boundary":
        fit["shift_east_m"] = 80
    elif kind == "worse":
        fit["after_heldout"]["rmse_m"] = 8
    elif kind == "missing_holdout":
        fit["heldout_cells"] = 0
    else:
        fit["shift_north_m"] = float("inf")
    assert not evaluate_gates(**evidence)["bounded_relative_registration"]


@pytest.mark.parametrize("kind", ["wrong_datum", "wrong_units", "no_transfer", "bad_schema", "skipped_tests", "no_tests", "wrong_sigma_unit"])
def test_missing_metadata_transfer_schema_or_test_evidence_fails(evidence, kind):
    if kind == "wrong_datum":
        evidence["vertical"]["products"]["MSL_Gale_DEM_Mosaic_1m_v3"]["vertical_datum"] = "guessed"
    elif kind == "wrong_units":
        evidence["vertical"]["products"]["DTEEC_019698_1750_019988_1750_U01"]["units"] = "km"
    elif kind == "no_transfer":
        evidence["transfer"]["passed"] = False
    elif kind == "bad_schema":
        evidence["stac"]["ok"] = False
    elif kind == "skipped_tests":
        evidence["tests"]["skipped"] = 1
    elif kind == "no_tests":
        evidence["tests"]["tests"] = 0
    else:
        evidence["comparison"]["slope_disagreement"]["unit"] = "m"
    assert not all(evaluate_gates(**evidence).values())
