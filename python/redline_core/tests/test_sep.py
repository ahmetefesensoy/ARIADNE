"""proje.md §7.12. The E-detector values below are the sol 4190 readings recorded in
proje.md §6.3; the six-hour background before them is a synthetic SCENARIO series.
The real RAD file is parsed and replayed in T6, not here."""
import math

import numpy as np
import pytest

from redline_core.sep import EMERGENCY, INFO, WARNING, background_median, evaluate, shelter_decision

CADENCE_S = 17 * 60.0


def quiet_then_event():
    quiet_t = np.arange(-6 * 3600.0, 0.0, CADENCE_S)
    # 5.5/5.6/5.7 cycle: the median stays 5.6 µGy/h when the window slides by one reading.
    quiet = np.array([5.5, 5.6, 5.7])[np.arange(quiet_t.size) % 3]
    event_t = np.array([0.0, 1025.0, 2051.0, 3077.0])  # 05:04:45, 05:21:50, 05:38:56, ...
    event = np.array([5.72, 9.97, 85.38, 214.04])
    return np.r_[quiet_t, event_t], np.r_[quiet, event]


def test_background_is_the_median_of_the_previous_six_hours():
    t, dose = quiet_then_event()
    assert background_median(t, dose, now_s=0.0) == pytest.approx(5.6)


def test_readings_older_than_the_window_do_not_count():
    t = np.array([-8 * 3600.0, -7 * 3600.0, -100.0])
    dose = np.array([50.0, 50.0, 5.0])
    assert background_median(t, dose, now_s=0.0) == pytest.approx(5.0)
    assert math.isnan(background_median(t[:2], dose[:2], now_s=0.0))


def test_alarm_first_fires_on_the_reading_above_125_percent_of_background():
    t, dose = quiet_then_event()
    first = None
    for now in (0.0, 1025.0, 2051.0):
        if evaluate({"E": (t, dose)}, now, detector="E").alert:
            first = now
            break
    assert first == 1025.0  # 9.97 ≥ 1.25 · 5.6 = 7.0; 5.72 is not


def test_both_detectors_are_reported_and_the_selected_one_decides():
    t, dose_e = quiet_then_event()
    dose_b = np.full_like(dose_e, 5.6)
    status = evaluate({"B": (t, dose_b), "E": (t, dose_e)}, 1025.0, detector="B")
    assert status.alert is False
    assert status.by_detector["E"].alert is True
    assert status.by_detector["B"].alert is False
    assert status.by_detector["E"].dose == pytest.approx(9.97)
    assert status.by_detector["E"].background == pytest.approx(5.6)


def test_unknown_detector_is_rejected():
    t, dose = quiet_then_event()
    with pytest.raises(ValueError, match="detector"):
        evaluate({"E": (t, dose)}, 0.0, detector="B")


@pytest.mark.parametrize(
    ("alert", "shelter_s", "severity", "recommend"),
    [(True, 25 * 60.0, EMERGENCY, True), (True, 15 * 60.0, WARNING, False), (False, 25 * 60.0, INFO, False)],
)
def test_shelter_rule_at_alarm(alert, shelter_s, severity, recommend):
    decision = shelter_decision(alert, shelter_s, t_sep_max_s=20 * 60.0)
    assert decision.severity == severity
    assert decision.recommend_return is recommend
