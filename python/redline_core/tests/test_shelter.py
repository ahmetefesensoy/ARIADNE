"""proje.md §7.7: time to shelter and the bottleneck DP golden test (§7.14)."""
import itertools
import math

import numpy as np
import pytest

from redline_core.shelter import bottleneck_plan, kappa_matrix, shelter_time


def brute_force(kappa, rover_time, dt, distance):
    k_count, c_count = kappa.shape
    best = (math.inf, math.inf)
    for seq in itertools.product(range(c_count), repeat=k_count):
        if any(rover_time[seq[k - 1], seq[k]] > dt[k] for k in range(1, k_count)):
            continue
        value = max(kappa[k, seq[k]] for k in range(k_count))
        dist = sum(distance[seq[k - 1], seq[k]] for k in range(1, k_count))
        best = min(best, (value, dist))
    return best


@pytest.mark.parametrize("seed", range(10))
def test_bottleneck_dp_matches_brute_force(seed):
    rng = np.random.default_rng(seed)
    k_count, c_count = 4, 6
    kappa = rng.integers(1, 12, (k_count, c_count)).astype(float)  # small integers force ties
    kappa[rng.random((k_count, c_count)) < 0.15] = math.inf
    rover_time = rng.uniform(0.0, 100.0, (c_count, c_count))
    np.fill_diagonal(rover_time, 0.0)
    distance = rng.integers(1, 9, (c_count, c_count)).astype(float)
    np.fill_diagonal(distance, 0.0)
    dt = np.array([0.0, 45.0, 45.0, 45.0])
    plan = bottleneck_plan(kappa, rover_time, dt, distance)
    want_value, want_distance = brute_force(kappa, rover_time, dt, distance)
    assert plan.value_s == want_value
    if math.isfinite(want_value):
        assert plan.distance_m == want_distance
        seq = plan.stations
        assert max(kappa[k, c] for k, c in enumerate(seq)) == want_value
        assert all(rover_time[seq[k - 1], seq[k]] <= dt[k] for k in range(1, k_count))
        assert sum(distance[seq[k - 1], seq[k]] for k in range(1, k_count)) == want_distance


def test_infeasible_plan_has_infinite_value_and_no_stations():
    plan = bottleneck_plan(np.full((2, 2), math.inf), np.zeros((2, 2)), np.zeros(2), np.zeros((2, 2)))
    assert plan.value_s == math.inf
    assert plan.stations == ()


def test_kappa_is_the_worst_rescue_time_in_each_segment_gated_by_line_of_sight():
    rescue = np.array([[10.0, 20.0, 30.0], [5.0, 50.0, 7.0]])  # stations × crew positions
    segments = [np.array([0, 1]), np.array([2])]
    los = np.array([[True, False, True], [True, True, True]])
    kappa = kappa_matrix(rescue, segments, los=los, rho=0.6)
    # Station 0 sees half of segment 0 (< 0.6) -> unusable there.
    np.testing.assert_array_equal(kappa, [[math.inf, 50.0], [30.0, 7.0]])


def test_shelter_time_is_the_faster_of_walking_and_rover_pickup():
    walk = np.array([600.0, 1500.0, math.inf])
    rover = np.array([900.0, 600.0, 1200.0])
    np.testing.assert_allclose(shelter_time(walk, rover, tau_al_s=300.0), [600.0, 900.0, 1500.0])
