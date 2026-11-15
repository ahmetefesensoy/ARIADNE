"""Debrief grade from run records (council 2026-11-15; D018 follow-up): axes stay separate, safety
caps the overall letter, and every axis names the records it came from."""
import math

import numpy as np
import pytest

from redline_core.debrief import SampleOutcome, Thresholds, Violation, grade

T = Thresholds(margin_min={"A": 30.0, "B": 10.0, "C": 0.0}, bits={"A": 1.0, "B": 0.5, "C": 0.1})
PRIOR = np.array([1 / 3, 1 / 3, 1 / 3])
SHARP = np.array([0.9, 0.05, 0.05])


def test_a_clean_run_with_a_sharp_posterior_and_a_recorded_sample_gets_a():
    out = grade(violations=[], min_margin_min=42.0, prior=PRIOR, posterior=SHARP,
                samples=[SampleOutcome("smp-1", "RECORDED")], thresholds=T)
    assert out["safety"]["letter"] == "A" and out["science"]["letter"] == "A" and out["overall"] == "A"
    expected_bits = math.log2(3) - float(-(SHARP * np.log2(SHARP)).sum())
    assert out["science"]["bits"] == pytest.approx(expected_bits)
    assert out["samples"] == {"letter": "A", "recorded": ["smp-1"], "failed": [], "in_progress": []}


def test_safety_caps_the_overall_letter_however_good_the_science():
    warn = Violation("viol-7", "FR-03", 2)  # WARNING: outside the SEP shelter limit
    out = grade(violations=[warn], min_margin_min=42.0, prior=PRIOR, posterior=SHARP, samples=[], thresholds=T)
    assert out["science"]["letter"] == "A" and out["safety"]["letter"] == "C" and out["overall"] == "C"
    assert out["safety"]["evidence"] == ["viol-7"]


def test_an_emergency_or_a_reserve_breach_fails_the_run():
    emergency = grade(violations=[Violation("v1", "FR-01", 3)], min_margin_min=42.0, prior=PRIOR,
                      posterior=SHARP, samples=[], thresholds=T)
    breach = grade(violations=[], min_margin_min=-0.5, prior=PRIOR, posterior=SHARP, samples=[], thresholds=T)
    assert emergency["overall"] == "F" and breach["overall"] == "F" and breach["safety"]["min_margin_min"] == -0.5


def test_cautions_and_a_thin_margin_lower_safety_by_one_step():
    caution = grade(violations=[Violation("v2", "FR-05", 1)], min_margin_min=42.0, prior=PRIOR, posterior=SHARP,
                    samples=[], thresholds=T)
    thin = grade(violations=[], min_margin_min=12.0, prior=PRIOR, posterior=SHARP, samples=[], thresholds=T)
    assert caution["safety"]["letter"] == "B" and thin["safety"]["letter"] == "B"


def test_no_measurement_means_no_science_credit_and_info_messages_do_not_count():
    out = grade(violations=[Violation("v3", "FR-12", 0)], min_margin_min=42.0, prior=PRIOR, posterior=PRIOR,
                samples=[SampleOutcome("smp-2", "FAILED"), SampleOutcome("smp-3", "ACQUIRED")], thresholds=T)
    assert out["safety"]["letter"] == "A" and out["science"]["bits"] == pytest.approx(0.0)
    assert out["science"]["letter"] == "D" and out["overall"] == "D"
    assert out["samples"]["letter"] == "B" and out["samples"]["failed"] == ["smp-2"]


def test_inputs_are_validated():
    with pytest.raises(ValueError):
        grade(violations=[], min_margin_min=math.nan, prior=PRIOR, posterior=SHARP, samples=[], thresholds=T)
    with pytest.raises(ValueError):
        grade(violations=[], min_margin_min=1.0, prior=PRIOR, posterior=np.array([0.5, 0.5]), samples=[],
              thresholds=T)
    with pytest.raises(ValueError):
        grade(violations=[Violation("v", "FR-01", 9)], min_margin_min=1.0, prior=PRIOR, posterior=SHARP,
              samples=[], thresholds=T)
