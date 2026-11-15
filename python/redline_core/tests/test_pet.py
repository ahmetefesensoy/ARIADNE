"""proje.md §7.8: plan timeline, return margins and cuff checklist."""
import numpy as np
import pytest

from redline_core.cost_human import CrewMember, SuitModel, WalkModel
from redline_core.pet import LegCost, PlanStation, build_timeline
from redline_core.redline import Resources
from redline_core.walkback import WalkbackField

CREW = CrewMember("EV1", body_mass_kg=70.0, load_mass_kg=35.0)
BIG = Resources(o2_kg=10.0, co2_capacity_kg=10.0, water_kg=100.0, battery_wh=10_000.0)
NONE = Resources(o2_kg=0.0, co2_capacity_kg=0.0, water_kg=0.0, battery_wh=0.0)
STATIONS = (
    PlanStation("S1", (0, 1), service_s=300.0, tasks=("PHOTO",)),
    PlanStation("S2", (0, 2), service_s=600.0, tasks=("LIBS", "APXS")),
)


def corridor_field():
    return WalkbackField(
        time_s=np.array([[0.0, 600.0, 1200.0]]),
        var_s2=np.array([[0.0, 100.0, 200.0]]),
        energy_per_kg_j=np.array([[0.0, 1000.0, 2000.0]]),
        distance_m=np.array([[0.0, 300.0, 600.0]]),
        next_hop=np.array([[-1, 0, 1]]),
    )


def every_leg(_start, _goal):
    return LegCost(time_s=600.0, var_s2=100.0, energy_per_kg_j=1000.0, distance_m=300.0)


def plan(initial=BIG, reserve=NONE, cost=every_leg):
    return build_timeline(
        "HAB", (0, 0), STATIONS, cost, corridor_field(), CREW, SuitModel(), WalkModel(), initial, reserve
    )


def test_timeline_accumulates_walking_and_service_time():
    timeline = plan()
    assert [(leg.from_id, leg.to_id) for leg in timeline.legs] == [("HAB", "S1"), ("S1", "S2")]
    np.testing.assert_allclose([leg.duration_s for leg in timeline.legs], [600.0, 600.0])
    np.testing.assert_allclose([leg.duration_sigma_s for leg in timeline.legs], [10.0, 10.0])
    np.testing.assert_allclose([leg.arrival_pet_s for leg in timeline.legs], [600.0, 1500.0])  # 600 + 300 + 600


def test_leg_consumables_follow_the_metabolic_model():
    # E = s·(1.5W + 2(W+L)(L/W)²)·600 + (W+L)·1000 + 335·0.0134·W·300 m = 247223.471 J (D010)
    leg = plan().legs[0]
    assert leg.o2_kg == pytest.approx(0.017580335716323177, rel=1e-12)


def test_return_margin_shrinks_away_from_shelter_and_sets_the_decision_pet():
    timeline = plan()
    first, second = timeline.legs
    assert first.return_margin_s > second.return_margin_s > 0.0
    for leg, entry in zip(timeline.legs, timeline.cuff):
        assert entry.station_id == leg.to_id
        assert entry.arrival_pet_s == leg.arrival_pet_s
        assert entry.return_decision_pet_s == pytest.approx(leg.arrival_pet_s + leg.return_margin_s)
    assert timeline.cuff[1].tasks == ("LIBS", "APXS")
    assert timeline.valid is True
    assert timeline.first_violation is None


def test_more_oxygen_buys_proportionally_more_margin_when_oxygen_limits():
    base = plan(initial=Resources(o2_kg=1.0, co2_capacity_kg=10.0, water_kg=100.0, battery_wh=10_000.0))
    more = plan(initial=Resources(o2_kg=1.1, co2_capacity_kg=10.0, water_kg=100.0, battery_wh=10_000.0))
    gained = [b.return_margin_s - a.return_margin_s for a, b in zip(base.legs, more.legs)]
    # Dwell = standing 79.924 W + task 335·0.008·70 = 267.524 W -> O2 1.9024e-5 kg/s;
    # 0.1 kg buys 5256.54 s (D010).
    np.testing.assert_allclose(gained, [5256.535405728354] * 2, rtol=1e-9)


def test_plan_without_headroom_above_reserve_is_invalid_at_first_station():
    timeline = plan(initial=BIG, reserve=BIG)
    assert timeline.valid is False
    assert timeline.first_violation == "S1"


def test_unreachable_leg_invalidates_the_plan():
    timeline = plan(cost=lambda start, goal: None if goal == (0, 2) else every_leg(start, goal))
    assert timeline.valid is False
    assert timeline.first_violation == "S2"
