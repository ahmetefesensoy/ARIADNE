"""Science rehearsal contracts: no invented archive values or custody shortcuts."""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

from redline_core.science_operations import (ProductStore, Sample, SampleState, ScienceTarget,
    checked_id, finite_point, load_targets, phase_at, phases_for, polygon_contains, posterior_grid, readiness_error,
    synthetic_measurement)


@pytest.fixture
def target():
    return ScienceTarget("T1", (1.0, 2.0, 3.0), {"SiO2": 40.0, "FeO": 20.0}, 1.5, 3.2,
                         ("scenario-test-seed-7",), 0.8)


def test_registry_explicit_provenance_and_no_archive_fallback(tmp_path):
    doc = {"seed": 7, "provenance_status": "SCENARIO", "noise_calibration": "UNCALIBRATED_SCENARIO",
        "targets": [{"id": "T1", "point_m": [1, 2, 3], "composition_percent": {"SiO2": 40},
                     "sigma_percent": 1.5, "weh_percent": 3.2, "input_ids": ["scenario-7"]}]}
    path = tmp_path / "targets.yaml"
    path.write_text(yaml.safe_dump(doc))
    seed, targets, _ = load_targets(path)
    assert seed == 7 and targets["T1"].point == (1.0, 2.0, 3.0)
    doc["provenance_status"] = "ARCHIVE"
    path.write_text(yaml.safe_dump(doc))
    with pytest.raises(ValueError, match="SCENARIO"):
        load_targets(path)


@pytest.mark.parametrize("value", ["../escape", "", "a/b", "a\\b", "a" * 129])
def test_persistent_paths_reject_untrusted_ids(value):
    with pytest.raises(ValueError):
        checked_id(value)


def test_points_and_phase_boundaries():
    with pytest.raises(ValueError):
        finite_point([1, math.nan, 3])
    phases = phases_for("DRILL", stall=True)
    assert phase_at(phases, 0, 10) == ("SELECTED", 0)
    assert phase_at(phases, 10, 10) == ("ACQUIRED", 1)
    assert "RETRACT" in phases and "PERCUSSIVE_RECOVERY" in phases
    with pytest.raises(ValueError):
        phase_at(phases, 1, 0)


def test_readiness_retains_all_gates():
    args = dict(active=True, simulated_enabled=True, physical_mode=False, pose=(1, 2, 3),
                age_s=0.1, target=(1, 2, 3), max_range_m=4, available_power_w=100, required_power_w=30)
    assert readiness_error(**args) == ""
    for changed, expected in (({"active": False}, "lifecycle"), ({"physical_mode": True}, "physical"),
                              ({"simulated_enabled": False}, "explicitly"), ({"age_s": 3}, "stale"),
                              ({"target": (100, 2, 3)}, "range"), ({"available_power_w": 1}, "power")):
        assert expected in readiness_error(**{**args, **changed})


def test_measurement_repeats_and_longer_integration_reduces_declared_noise(target):
    first = synthetic_measurement(target, "APXS", "request-1", 7, 20)
    assert first == synthetic_measurement(target, "APXS", "request-1", 7, 20)
    second = synthetic_measurement(target, "APXS", "request-2", 7, 80)
    assert second["sigma"][0] == pytest.approx(first["sigma"][0] / 2)
    assert first["noise_calibration"] == "UNCALIBRATED_SCENARIO"
    assert "no NASA" in first["limitation"]
    assert synthetic_measurement(target, "WEATHER", "request-3", 7)["values"] == []
    with pytest.raises(ValueError):
        synthetic_measurement(target, "UNKNOWN", "request-4", 7)


def test_sample_chain_never_confuses_origin_with_analysis(target):
    sample = Sample("smp-T1-1", "T1", target.point, (8, 9, 10), "SCOOP_SCENARIO")
    with pytest.raises(ValueError, match="skip"):
        sample.advance(SampleState.ACQUIRED)
    for state in (SampleState.REACH_OK, SampleState.PRE_POSITIONED, SampleState.READY,
                  SampleState.ACQUIRING, SampleState.ACQUIRED):
        sample.advance(state)
    with pytest.raises(ValueError, match="container"):
        sample.advance(SampleState.STOWED)
    sample.container_id = "tube-1"
    sample.advance(SampleState.STOWED)
    sample.analysis_point = (50, 20, 10)
    sample.advance(SampleState.RECORDED)
    assert sample.origin_point == target.point and sample.analysis_point != sample.origin_point
    with pytest.raises(ValueError, match="terminal"):
        sample.advance(SampleState.FAILED)


def test_request_repeat_survives_store_recreation(tmp_path):
    store = ProductStore(tmp_path, "run-1")
    assert store.reserve_request("rq-1")
    assert not ProductStore(tmp_path, "run-1").reserve_request("rq-1")


def test_product_label_hash_and_input_lineage(tmp_path, target):
    store = ProductStore(tmp_path, "run-1")
    payload = store.write(request_id="rq-1", instrument="LIBS", target=target,
        measured_utc="2026-11-15T00:00:00Z", integration_s=20, instrument_point=(4, 5, 6),
        measurement=synthetic_measurement(target, "LIBS", "rq-1", 7))
    path = Path(payload["payload_uri"])
    assert payload["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    label = ET.parse(path.with_suffix(".xml")).getroot()
    assert label.findtext("json_sha256") == payload["sha256"]
    doc = json.loads(path.read_text())
    assert doc["provenance_status"] == "SIMULATED" and doc["input_ids"] == ["scenario-test-seed-7"]
    assert doc["target_point_m"] != doc["instrument_point_m"]
    with pytest.raises(ValueError, match="already exists"):
        store.write(request_id="rq-1", instrument="LIBS", target=target, measured_utc="now",
                    integration_s=20, instrument_point=(4, 5, 6), measurement={})


def test_gaussian_process_posterior_is_bounded_finite_and_uncertainty_varies():
    grid = posterior_grid([(0, 0, 0), (4, 4, 0)], [2.0, 4.0], 0.2, size=9)
    assert len(grid["values"]) == len(grid["sigma"]) == 81
    assert all(math.isfinite(v) for v in grid["values"] + grid["sigma"])
    assert min(grid["sigma"]) < max(grid["sigma"])
    assert grid["status"] == "SIMULATED"
    with pytest.raises(ValueError):
        posterior_grid([], [], 1)


def test_neutron_polygon_never_grants_an_outside_observation():
    square = [(0, 0), (4, 0), (4, 4), (0, 4)]
    assert polygon_contains((1, 1), square)
    assert polygon_contains((4, 2), square)
    assert not polygon_contains((5, 2), square)
    with pytest.raises(ValueError):
        polygon_contains((0, 0), [(0, 0)] * 3)


def test_sample_product_embeds_self_evidence_and_prior_chain(tmp_path, target):
    sample = Sample("smp-1", "T1", target.point, (20, 30, 40), "SCOOP_SCENARIO",
                    "tube-1", SampleState.RECORDED, ["ev-collection"])
    payload = ProductStore(tmp_path, "run-1").write(request_id="cache-1", instrument="SAMPLE",
        target=target, measured_utc="2026-11-15T00:00:00Z", integration_s=20,
        instrument_point=sample.analysis_point, measurement={}, sample=sample)
    assert payload["sample"]["evidence_ids"] == ["ev-collection", payload["evidence_id"]]
    assert "ev-collection" in payload["input_ids"]
