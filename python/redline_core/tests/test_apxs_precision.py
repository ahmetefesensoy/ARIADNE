"""APXS precision model (proje.md §9.1/§9.2 B1): a DERIVED fit of the ARCHIVE MSL APXS supplement.

log σ = log σ_ref + exp_t·log(t/t_ref) + exp_v·log(v/v_ref) + per_cm_standoff·max(standoff, 0)
"""
import json
import math

import pytest

from redline_core.apxs_precision import SCHEMA, ApxsPrecision

SOURCE = {"url": "https://example.invalid/ds01.csv", "sha256": "0" * 64, "doi": "10.1029/2020JE006536"}


def model_dict(**over):
    data = {"schema": SCHEMA, "provenance_status": "DERIVED", "source": SOURCE, "t_ref_s": 3600.0,
            "calibrated_integration_s": [540.0, 41657.0], "calibrated_standoff_cm": [0.0, 5.6],
            "oxides": {"SiO2": {"v_ref_wt": 45.0, "sigma_ref_wt": 0.5, "exp_t": -0.1, "exp_v": 0.8,
                                "per_cm_standoff": 0.05, "mad_log": 0.08, "n": 690},
                       "FeO": {"v_ref_wt": 19.0, "sigma_ref_wt": 0.2, "exp_t": 0.0, "exp_v": 0.78,
                               "per_cm_standoff": 0.04, "mad_log": 0.1, "n": 690}}}
    data.update(over)
    return data


@pytest.fixture
def model(tmp_path):
    path = tmp_path / "apxs.json"
    path.write_text(json.dumps(model_dict()))
    return ApxsPrecision.load(path)


def test_sigma_at_the_reference_point_is_the_reference_error(model):
    assert model.sigma_wt("SiO2", 45.0, 3600.0) == pytest.approx(0.5)


def test_sigma_follows_the_fitted_power_law_in_time_abundance_and_standoff(model):
    expected = 0.5 * 2.0 ** -0.1 * (30.0 / 45.0) ** 0.8 * math.exp(0.05 * 2.0)
    assert model.sigma_wt("SiO2", 30.0, 7200.0, standoff_cm=2.0) == pytest.approx(expected)


def test_a_compressed_contact_sensor_counts_as_touching(model):
    # The supplement records negative standoff when the contact sensor is pressed in.
    assert model.sigma_wt("SiO2", 45.0, 3600.0, standoff_cm=-0.3) == pytest.approx(0.5)


def test_an_oxide_whose_error_does_not_shrink_with_time_gains_nothing_from_a_longer_count(model):
    assert model.sigma_wt("FeO", 19.0, 600.0) == pytest.approx(model.sigma_wt("FeO", 19.0, 36000.0))


def test_integration_outside_the_calibrated_range_is_refused(model):
    with pytest.raises(ValueError, match="calibrated"):
        model.sigma_wt("SiO2", 45.0, 60.0)
    with pytest.raises(ValueError, match="calibrated"):
        model.sigma_wt("SiO2", 45.0, 3600.0, standoff_cm=9.0)


def test_unknown_oxide_and_non_positive_abundance_are_refused(model):
    with pytest.raises(KeyError):
        model.sigma_wt("UO2", 1.0, 3600.0)
    with pytest.raises(ValueError):
        model.sigma_wt("SiO2", 0.0, 3600.0)


def test_loader_requires_the_schema_and_a_derived_status(tmp_path):
    for bad in (model_dict(schema="other"), model_dict(provenance_status="SCENARIO")):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError):
            ApxsPrecision.load(path)


def test_provenance_names_the_archive_source(model):
    assert model.provenance()["status"] == "DERIVED"
    assert model.provenance()["source_sha256"] == "0" * 64 and "2020JE006536" in model.provenance()["doi"]
