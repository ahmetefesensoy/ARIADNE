"""ev_sim core: motion window, consumption and PET depletion; mission clock runner."""
import math

import pytest

from redline_core.cost_human import CrewMember, SuitModel, WalkModel, metabolic_power
from redline_core.mission_clock import MissionClockRunner, split_seconds
from redline_core.redline import Rates, Resources
from redline_core.suit_state import Motion, MotionWindow, consumption, deplete

WALK = WalkModel()
SUIT = SuitModel()
CREW = CrewMember("EV1", body_mass_kg=75.0, load_mass_kg=80.0)


def test_window_speed_and_grade_over_the_window():
    w = MotionWindow(window_s=2.0)
    for i in range(11):  # 0.5 m/s east, climbing 0.05 m per metre
        t = 0.2 * i
        w.add(t, 0.5 * t, 0.0, 0.025 * t)
    m = w.motion(WALK)
    assert m.speed_m_s == pytest.approx(0.5)
    assert m.grade_percent == pytest.approx(5.0)
    assert not m.capped and w.position == pytest.approx((1.0, 0.0, 0.05))


def test_window_keeps_only_recent_samples():
    w = MotionWindow(window_s=1.0)
    w.add(0.0, 0.0, 0.0, 0.0)
    w.add(5.0, 5.0, 0.0, 0.0)  # 1 m/s for the first 5 s
    w.add(5.5, 5.0, 0.0, 0.0)              # then stands still
    w.add(6.5, 5.0, 0.0, 0.0)
    assert w.motion(WALK).speed_m_s == pytest.approx(0.0)


def test_standing_still_and_single_samples_give_zero_motion():
    w = MotionWindow()
    assert w.motion(WALK) == Motion(0.0, 0.0, False) and w.position is None
    w.add(0.0, 1.0, 2.0, 3.0)
    assert w.motion(WALK) == Motion(0.0, 0.0, False)
    w.add(1.0, 1.0, 2.0, 3.5)  # vertical-only change is not a grade over zero run
    assert w.motion(WALK).grade_percent == 0.0


def test_speed_is_capped_at_the_walk_run_transition():
    w = MotionWindow()
    w.add(0.0, 0.0, 0.0, 0.0)
    w.add(1.0, 3.0, 0.0, 0.0)
    m = w.motion(WALK)
    assert m.capped and m.speed_m_s == pytest.approx(WALK.walk_run_speed_m_s)


def test_explicit_scenario_sprint_is_metered_without_changing_default_walking():
    walking, sprint = MotionWindow(), MotionWindow(scenario_speed_cap_m_s=3.0)
    for window in (walking, sprint):
        window.add(0.0, 0.0, 0.0, 0.0)
        window.add(1.0, 3.0, 0.0, 0.0)
    observed = sprint.motion(WALK)
    assert observed == Motion(3.0, 0.0, False)
    default = walking.motion(WALK)
    assert default.capped and default.speed_m_s == pytest.approx(WALK.walk_run_speed_m_s)
    sprint_power, sprint_rates = consumption(observed, 1.0, CREW, SUIT, WALK)
    walking_power, walking_rates = consumption(default, 1.0, CREW, SUIT, WALK)
    assert sprint_power == pytest.approx(metabolic_power(3.0, 0.0, 1.0, CREW, SUIT, WALK))
    assert sprint_power > walking_power and sprint_rates.o2_kg_s > walking_rates.o2_kg_s
    # The explicit demo cap still rejects arbitrarily fast pose motion.
    sprint.add(2.0, 7.0, 0.0, 0.0)
    assert sprint.motion(WALK) == Motion(3.0, 0.0, True)


@pytest.mark.parametrize("cap", [0.0, -1.0, math.nan, math.inf, 5.01])
def test_scenario_sprint_cap_rejects_unbounded_or_invalid_configuration(cap):
    with pytest.raises(ValueError, match="SCENARIO speed cap"):
        MotionWindow(scenario_speed_cap_m_s=cap)


def test_a_teleport_resets_the_window_and_old_samples_are_ignored():
    w = MotionWindow(max_step_m=10.0)
    w.add(0.0, 0.0, 0.0, 0.0)
    w.add(1.0, 50.0, 0.0, 0.0)
    assert w.resets == 1 and w.motion(WALK).speed_m_s == 0.0
    w.add(0.5, 0.0, 0.0, 0.0)  # older than the last sample: dropped
    assert w.position == (50.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        w.add(2.0, math.nan, 0.0, 0.0)


def test_consumption_uses_the_spec_metabolic_model():
    motion = Motion(0.8, 4.0, False)
    power, rates = consumption(motion, 1.1, CREW, SUIT, WALK)
    assert power == pytest.approx(metabolic_power(0.8, 4.0, 1.1, CREW, SUIT, WALK))
    assert rates == Rates.from_metabolic_power(power, SUIT)
    standing, _ = consumption(Motion(0.0, 0.0, False), 1.1, CREW, SUIT, WALK)
    assert standing < power


def test_deplete_integrates_rates_and_floors_at_empty():
    start = Resources(o2_kg=1.0, co2_capacity_kg=1.0, water_kg=2.0, battery_wh=100.0)
    rates = Rates(o2_kg_s=1e-4, co2_kg_s=2e-4, water_kg_s=1e-3, battery_w=360.0)
    after = deplete(start, rates, 100.0)
    assert after == Resources(o2_kg=pytest.approx(0.99), co2_capacity_kg=pytest.approx(0.98),
                              water_kg=pytest.approx(1.9), battery_wh=pytest.approx(90.0))
    assert deplete(start, rates, 1e6) == Resources(0.0, 0.0, 0.0, 0.0)
    assert deplete(start, rates, 0.0) == start
    with pytest.raises(ValueError):
        deplete(start, rates, -1.0)


def test_mission_clock_scales_pauses_and_stays_continuous():
    c = MissionClockRunner(start_s=60.0, scale=1.0, now_monotonic_s=100.0)
    assert c.pet(100.0) == 60.0 and c.pet(110.0) == 70.0
    c.set_scale(10.0, 110.0)
    assert c.pet(110.0) == 70.0 and c.pet(111.0) == 80.0
    c.pause(111.0)
    assert not c.running and c.pet(500.0) == 80.0
    c.resume(500.0)
    assert c.pet(501.0) == 90.0
    assert c.pet(400.0) == 80.0  # monotonic input before the anchor never moves PET back


@pytest.mark.parametrize("kwargs", [dict(start_s=-1.0, scale=1.0), dict(start_s=0.0, scale=0.0),
                                    dict(start_s=0.0, scale=math.inf)])
def test_mission_clock_rejects_bad_parameters(kwargs):
    with pytest.raises(ValueError):
        MissionClockRunner(now_monotonic_s=0.0, **kwargs)


def test_split_seconds_fills_builtin_time_fields():
    assert split_seconds(12.25) == (12, 250_000_000)
    assert split_seconds(0.9999999999) == (0, 999_999_999)
    with pytest.raises(ValueError):
        split_seconds(-0.5)


def test_mission_clock_pause_and_resume_are_idempotent():
    c = MissionClockRunner(start_s=0.0, scale=2.0, now_monotonic_s=0.0)
    c.resume(5.0)  # already running: no effect
    assert c.pet(10.0) == 20.0
    c.pause(10.0)
    c.pause(12.0)  # already paused: no effect
    assert c.pet(50.0) == 20.0
    c.resume(50.0)
    assert c.pet(51.0) == 22.0
