"""SIMULATED crew motion along a plan on PET (D015): schedule, trail, walk home. Hand values."""
import numpy as np
import pytest

from core_helpers import terrain_grid
from redline_core.cost_human import DETECTED, WalkModel, edge_cost, prepare_terrain
from redline_core.plan_follow import PlanSchedule, TimedPath, timed_path_from_cells

ROUTE = np.array([[0.0, 0.0], [50.0, 0.0], [100.0, 0.0], [50.0, 0.0], [0.0, 0.0]])


def schedule(start=1000.0):
    # HAB → S1 (100 s walk), 60 s service, S1 → HAB (100 s walk)
    return PlanSchedule.from_plan(ROUTE, [((100.0, 0.0), 60.0)], [100.0, 100.0], start)


def test_timed_path_interpolates_position_by_time():
    path = TimedPath(np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 20.0]]), np.array([0.0, 10.0, 30.0]))
    assert path.position(-5.0) == (0.0, 0.0)
    assert path.position(5.0) == pytest.approx((5.0, 0.0))
    assert path.position(20.0) == pytest.approx((10.0, 10.0))
    assert path.position(99.0) == (10.0, 20.0) and path.duration_s == 30.0


def test_schedule_walks_serves_and_returns_on_the_planned_times():
    s = schedule()
    assert s.at(900.0) == ((0.0, 0.0), "home", -1)  # before egress
    assert s.at(1050.0)[:2] == (pytest.approx((50.0, 0.0)), "walk")
    assert s.at(1130.0) == (pytest.approx((100.0, 0.0)), "service", 0)
    xy, activity, leg = s.at(1210.0)
    assert xy == pytest.approx((50.0, 0.0)) and activity == "walk" and leg == 1
    assert s.at(1400.0)[1] == "home" and s.end_pet_s == pytest.approx(1000.0 + 100 + 60 + 100)


def test_a_trailing_crew_member_is_the_same_schedule_later():
    s = schedule()
    assert s.at(1050.0, trail_s=20.0)[0] == pytest.approx(s.at(1030.0)[0])


def test_route_must_pass_every_station_in_order():
    with pytest.raises(ValueError, match="station"):
        PlanSchedule.from_plan(ROUTE, [((100.0, 40.0), 60.0)], [100.0, 100.0], 0.0)
    with pytest.raises(ValueError, match="legs"):
        PlanSchedule.from_plan(ROUTE, [((100.0, 0.0), 60.0)], [100.0], 0.0)


def test_walk_home_is_timed_with_the_terrain_model():
    walk = WalkModel()
    grid = terrain_grid(np.zeros((5, 5)), 4.0, state=DETECTED)
    terrain = prepare_terrain(grid, walk)
    cells = [(2, 4), (2, 3), (2, 2)]
    path = timed_path_from_cells(terrain, grid, cells, start_s=10.0)
    step = edge_cost(terrain, (2, 4), (0, -1)).time_s
    assert path.times_s == pytest.approx([10.0, 10.0 + step, 10.0 + 2 * step])
    assert path.position(10.0 + step) == pytest.approx(grid.cell_center(2, 3))
