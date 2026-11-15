"""Nominal EVA flow (proje.md §8.7; D015): BRIEFING → PRECURSOR → TRAVERSE ⇄ STATION_SCIENCE → RETURN → DEBRIEF."""
import numpy as np

from redline_core.mission_flow import (BRIEFING, CONTINGENCY, DEBRIEF, PRECURSOR, RETURN, STATION_SCIENCE,
                                       TRAVERSE, NominalFlow)
from redline_core.plan_follow import PlanSchedule

ROUTE = np.array([[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 0.0]])
STATIONS = [((100.0, 0.0), 60.0), ((100.0, 100.0), 60.0)]


def flow(precursor=False):
    f = NominalFlow(("EV1", "EV2"), shelter_xy=(0.0, 0.0), precursor=precursor)
    f.begin(PlanSchedule.from_plan(ROUTE, STATIONS, [100.0, 100.0, 140.0], 0.0))
    return f


def both(xy):
    return {"EV1": xy, "EV2": xy}


def test_briefing_goes_to_precursor_or_traverse_once_a_plan_exists():
    assert flow().step(BRIEFING, 0.0, both((0, 0)), plan_ready=False) is None
    assert flow().step(BRIEFING, 0.0, both((0, 0)), plan_ready=True)[0] == TRAVERSE
    f = flow(precursor=True)
    assert f.step(BRIEFING, 0.0, both((0, 0)), plan_ready=True)[0] == PRECURSOR
    assert f.step(PRECURSOR, 0.0, both((0, 0)), plan_ready=True, precursor_done=False) is None
    assert f.step(PRECURSOR, 0.0, both((0, 0)), plan_ready=True, precursor_done=True)[0] == TRAVERSE


def test_station_science_needs_the_schedule_and_every_crew_member_at_the_station():
    f = flow()
    assert f.step(TRAVERSE, 50.0, both((50, 0))) is None
    assert f.step(TRAVERSE, 110.0, {"EV1": (100, 0), "EV2": (60, 0)}) is None  # EV2 not there yet
    phase, context = f.step(TRAVERSE, 110.0, both((100, 0)))
    assert phase == STATION_SCIENCE and "S1" in context
    assert f.step(STATION_SCIENCE, 150.0, both((100, 0))) is None
    assert f.step(STATION_SCIENCE, 160.0, both((100, 0)))[0] == TRAVERSE


def test_the_last_station_leads_to_return_and_home_to_debrief():
    f = flow()
    assert f.step(TRAVERSE, 270.0, both((100, 100)))[0] == STATION_SCIENCE  # station 2 at 260–320 s
    assert f.step(STATION_SCIENCE, 320.0, both((100, 100)))[0] == RETURN
    assert f.step(RETURN, 400.0, {"EV1": (3, 0), "EV2": (40, 0)}) is None
    assert f.step(RETURN, 460.0, both((2, 1)))[0] == DEBRIEF


def test_contingency_and_debrief_are_not_nominal_transitions():
    f = flow()
    assert f.step(CONTINGENCY, 110.0, both((100, 0))) is None
    assert f.step(DEBRIEF, 900.0, both((0, 0))) is None
