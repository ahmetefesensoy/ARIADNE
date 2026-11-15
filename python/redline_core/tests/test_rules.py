"""FR-04 / FR-01 / FR-12 trackers on PET (proje.md §12)."""
import math

from redline_core.rules import Fr01Tracker, Fr04Tracker, Fr12Tracker


def test_fr04_satisfied_within_the_window_reports_latency_once():
    t = Fr04Tracker(30.0)
    assert t.update(100.0, False, False) is None
    assert t.update(110.0, True, False) is None  # alarm at PET 110
    assert t.update(125.0, True, True) == "satisfied" and t.latency_s == 15.0
    assert t.update(130.0, True, True) is None


def test_fr04_violated_after_the_window_and_late_compliance_is_marked():
    t = Fr04Tracker(30.0)
    t.update(0.0, True, False)
    assert t.update(29.0, True, False) is None
    assert t.update(31.0, True, False) == "violated"
    assert t.update(40.0, True, False) is None
    assert t.update(45.0, True, True) == "late" and t.latency_s == 45.0


def test_fr04_rearms_on_a_new_alarm():
    t = Fr04Tracker(30.0)
    t.update(0.0, True, True)
    t.update(10.0, False, True)
    assert t.update(100.0, True, False) is None and t.alarm_pet_s == 100.0
    assert t.update(140.0, True, False) == "violated"


def test_fr01_reports_crossings_and_ignores_unknown_positions():
    t = Fr01Tracker()
    assert t.update(12.0) is None
    assert t.update(math.nan) is None
    assert t.update(-0.5) == "violated"
    assert t.update(-3.0) is None
    assert t.update(1.0) == "cleared"
    assert t.update(-math.inf) == "violated"  # SEP: outside the shelter limit


def test_fr12_satisfied_when_everyone_is_inside_at_the_dusk_limit():
    t = Fr12Tracker()
    assert t.update(600.0, ["EV1"]) is None  # 10 min before the limit, still outside: allowed
    assert t.update(10.0, []) is None
    assert t.update(0.0, []) == "satisfied"  # the limit itself counts as reached
    assert t.update(-60.0, []) is None and t.update(-math.inf, []) is None  # once per limit


def test_fr12_violation_clears_when_the_crew_is_back_and_rearms():
    t = Fr12Tracker()
    assert t.update(-1.0, ["EV1", "EV2"]) == "violated"
    assert t.update(-30.0, ["EV2"]) is None
    assert t.update(-60.0, []) == "cleared" and not t.violated
    assert t.update(-90.0, ["EV1"]) == "violated"  # going out again after dusk
    assert t.update(math.nan, ["EV1"]) is None and t.violated  # outside the sun table: unknown
    assert t.update(36000.0, ["EV1"]) == "cleared"  # next day's budget


def test_fr12_before_sunrise_is_past_the_limit():
    assert Fr12Tracker().update(-math.inf, ["EV1"]) == "violated"


def test_fr05_caution_then_warning_after_the_grace_and_cleared_when_back():
    from redline_core.rules import Fr05Tracker
    t = Fr05Tracker(max_distance_m=100.0, grace_s=60.0, hysteresis_m=0.5)
    assert t.update(0.0, 40.0, 2.0) is None
    assert t.update(10.0, 120.0, 2.0) == "caution"  # too far
    assert t.update(50.0, 120.0, 2.0) is None
    assert t.update(70.0, 120.0, 2.0) == "warning"  # still apart 60 s later
    assert t.update(80.0, 120.0, 2.0) is None
    assert t.update(90.0, 50.0, 2.0) == "cleared"


def test_fr05_line_of_sight_uses_hysteresis_on_clearance():
    from redline_core.rules import Fr05Tracker
    t = Fr05Tracker(max_distance_m=100.0, grace_s=60.0, hysteresis_m=0.5)
    assert t.update(0.0, 30.0, -0.2) is None  # within the band: still counted as visible
    assert t.update(1.0, 30.0, -0.6) == "caution"  # below −0.5 m: line of sight lost
    assert t.update(2.0, 30.0, 0.3) is None  # back above 0 but not above +0.5 m: still lost
    assert t.update(3.0, 30.0, 0.6) == "cleared"
    assert t.update(4.0, 30.0, float("nan")) is None  # unknown terrain clearance: no event


def test_fr05_distance_uses_hysteresis_so_the_limit_does_not_flap():
    # S0b (BXW): 104 m → restored 6 s later; a 2 m band keeps one record per real separation.
    from redline_core.rules import Fr05Tracker
    t = Fr05Tracker(max_distance_m=100.0, grace_s=60.0, hysteresis_m=0.5, distance_hysteresis_m=2.0)
    assert t.update(0.0, 101.0, 2.0) == "caution"
    assert t.update(6.0, 99.0, 2.0) is None  # back under 100 m but inside the band: still apart
    assert t.update(8.0, 97.5, 2.0) == "cleared"
    assert t.update(9.0, 100.5, 2.0) == "caution"  # above the limit again


# --- S2 (proje.md §8.7 SUIT_LEAK, §16 S2): a suit leak detected from telemetry -----------------------
import pytest  # noqa: E402

from redline_core.rules import LeakTracker  # noqa: E402


def test_a_leak_is_detected_only_after_the_ratio_stays_high_for_the_hold_time():
    leak = LeakTracker(factor_on=1.5, factor_off=1.2, hold_s=30.0)
    assert leak.update(0.0, 1.0) is None
    assert leak.update(10.0, 3.0) is None  # high, but not yet for 30 s
    assert leak.update(39.0, 3.0) is None
    assert leak.update(40.0, 3.0) == "detected" and leak.detected and leak.detected_pet_s == 40.0
    assert leak.update(50.0, 3.0) is None  # one event per leak


def test_a_short_spike_does_not_count_and_restarts_the_hold():
    leak = LeakTracker(factor_on=1.5, factor_off=1.2, hold_s=30.0)
    leak.update(0.0, 2.0)
    leak.update(20.0, 1.0)  # back to normal before the hold time
    assert leak.update(40.0, 2.0) is None and leak.update(69.0, 2.0) is None
    assert leak.update(70.0, 2.0) == "detected"


def test_clearing_needs_the_ratio_below_the_lower_threshold():
    leak = LeakTracker(factor_on=1.5, factor_off=1.2, hold_s=0.0)
    assert leak.update(0.0, 1.6) == "detected"
    assert leak.update(1.0, 1.3) is None and leak.detected  # inside the hysteresis band
    assert leak.update(2.0, 1.1) == "cleared" and not leak.detected


def test_missing_telemetry_neither_detects_nor_clears():
    leak = LeakTracker(factor_on=1.5, factor_off=1.2, hold_s=10.0)
    leak.update(0.0, 2.0)
    assert leak.update(5.0, math.nan) is None
    assert leak.update(12.0, 2.0) is None  # the hold restarted at the gap
    assert leak.update(22.0, 2.0) == "detected"
    assert leak.update(23.0, math.nan) is None and leak.detected


def test_thresholds_must_form_a_hysteresis_band():
    with pytest.raises(ValueError):
        LeakTracker(factor_on=1.2, factor_off=1.5)
    with pytest.raises(ValueError):
        LeakTracker(factor_on=1.5, factor_off=0.9)
