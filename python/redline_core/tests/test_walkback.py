"""proje.md §7.5 and the §7.14 golden tests for the return field."""
import math
from dataclasses import replace

import networkx as nx
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core_helpers import V_FLAT, terrain_grid
from redline_core.cost_human import CrewMember, SuitModel, WalkModel, edge_cost, prepare_terrain
from redline_core.grid import neighbors16
from redline_core.walkback import WalkbackField, leg_cost, walkable_components, walkback

CREW = CrewMember("EV1", body_mass_kg=70.0, load_mass_kg=35.0, theta=1.0)


def inclined_plane(n=41, res=4.0, grade=0.1):
    x = (np.arange(n) - n // 2) * res
    z = np.tile(grade * x, (n, 1))  # rises toward +x (east)
    slope = np.full((n, n), math.degrees(math.atan(grade)))
    return prepare_terrain(terrain_grid(z, res, slope_deg=slope), WalkModel())


def random_terrain(seed=7, n=10):
    rng = np.random.default_rng(seed)
    z = rng.normal(0.0, 0.4, (n, n)).cumsum(axis=0) + rng.normal(0.0, 0.4, (n, n)).cumsum(axis=1)
    state = rng.integers(0, 3, (n, n)).astype(np.uint8)
    slope = rng.uniform(0.0, 20.0, (n, n))
    slope[2, 3] = 30.0
    slope[6, 6] = 27.0
    slope[0, 0] = slope[9, 5] = 0.0
    sigma = rng.uniform(0.0, 2.0, (n, n))
    return prepare_terrain(terrain_grid(z, 4.0, state=state, slope_deg=slope, sigma_deg=sigma), WalkModel())


def valid_edges(terrain, shape):
    h, w = shape
    for iy in range(h):
        for ix in range(w):
            for dy, dx in neighbors16():
                jy, jx = iy + dy, ix + dx
                if 0 <= jy < h and 0 <= jx < w:
                    cost = edge_cost(terrain, (iy, ix), (dy, dx))
                    if cost is not None:
                        yield (iy, ix), (jy, jx), cost


def test_flat_plane_walkback_is_distance_over_flat_speed():
    n, res = 41, 4.0
    field = walkback(prepare_terrain(terrain_grid(np.zeros((n, n)), res), WalkModel()), [(20, 20)])
    assert field.time_s[20, 30] == pytest.approx(46.41338879174768, rel=1e-9)  # 10 cells east
    assert field.time_s[30, 30] == pytest.approx(65.63844390498497, rel=1e-9)  # 10 diagonal steps
    assert field.time_s[30, 40] == pytest.approx(103.78349240447464, rel=1e-9)  # 10 knight steps
    # Off the 16 primitive directions the grid metric exceeds Euclidean by < 2.75 %.
    iy, ix = np.mgrid[0:n, 0:n]
    euclid = res * np.hypot(iy - 20, ix - 20) / V_FLAT
    mask = euclid > 0
    ratio = field.time_s[mask] / euclid[mask]
    assert ratio.min() >= 1.0 - 1e-12
    assert ratio.max() <= 1.0275


def test_inclined_plane_return_is_faster_downhill_than_uphill():
    field = walkback(inclined_plane(), [(20, 20)])
    east = field.time_s[20, 30]  # higher ground: the walk back is downhill
    west = field.time_s[20, 10]  # lower ground: the walk back is uphill
    assert east == pytest.approx(40.0 / 0.8618202859411123, rel=1e-9)
    assert west == pytest.approx(65.86373385461116, rel=1e-9)
    assert west > east


def test_multi_source_dijkstra_matches_networkx_brute_force():
    terrain = random_terrain()
    shelters = [(0, 0), (9, 5)]
    field = walkback(terrain, shelters)
    graph = nx.DiGraph()
    for a, b, cost in valid_edges(terrain, (10, 10)):
        graph.add_edge(a, b, weight=cost.time_s)
    want = nx.multi_source_dijkstra_path_length(graph.reverse(copy=True), set(shelters), weight="weight")
    for iy in range(10):
        for ix in range(10):
            if (iy, ix) in want:
                assert field.time_s[iy, ix] == pytest.approx(want[(iy, ix)], rel=1e-9, abs=1e-9)
            else:
                assert math.isinf(field.time_s[iy, ix])
    assert np.isinf(field.time_s[2, 3])  # banned cell


def test_labels_are_carried_along_the_next_hop_path():
    terrain = random_terrain()
    field = walkback(terrain, [(0, 0), (9, 5)])
    width = 10
    checked = 0
    for iy in range(10):
        for ix in range(10):
            if not math.isfinite(field.time_s[iy, ix]) or field.time_s[iy, ix] == 0.0:
                continue
            t = var = energy = distance = 0.0
            cy, cx = iy, ix
            while field.next_hop[cy, cx] >= 0:
                ny, nx_ = divmod(int(field.next_hop[cy, cx]), width)
                cost = edge_cost(terrain, (cy, cx), (ny - cy, nx_ - cx))
                t, var, energy = t + cost.time_s, var + cost.var_s2, energy + cost.energy_per_kg_j
                distance += cost.distance_m
                cy, cx = ny, nx_
            assert field.time_s[cy, cx] == 0.0
            assert t == pytest.approx(field.time_s[iy, ix], rel=1e-12)
            assert var == pytest.approx(field.var_s2[iy, ix], rel=1e-12, abs=1e-15)
            assert energy == pytest.approx(field.energy_per_kg_j[iy, ix], rel=1e-12)
            assert distance == pytest.approx(field.distance_m[iy, ix], rel=1e-12)
            checked += 1
    assert checked > 50


@settings(max_examples=40, deadline=None)
@given(st.integers(2, 6), st.integers(2, 6), st.integers(0, 2**32 - 1))
def test_walkback_is_nonnegative_and_bellman_consistent(height, width, seed):
    rng = np.random.default_rng(seed)
    slope = rng.uniform(0.0, 24.0, (height, width))
    slope[0, 0] = 0.0
    grid = terrain_grid(
        rng.uniform(-1.5, 1.5, (height, width)),
        4.0,
        state=rng.integers(0, 3, (height, width)).astype(np.uint8),
        slope_deg=slope,
        sigma_deg=rng.uniform(0.0, 1.0, (height, width)),
    )
    terrain = prepare_terrain(grid, WalkModel())
    t = walkback(terrain, [(0, 0)]).time_s
    assert t[0, 0] == 0.0
    assert np.all(t >= 0.0)
    for a, b, cost in valid_edges(terrain, (height, width)):
        if math.isfinite(t[b]):
            assert t[a] <= cost.time_s + t[b] + 1e-9


def test_cells_behind_a_banned_ring_are_unreachable():
    slope = np.zeros((9, 9))
    slope[2, 2:7] = slope[6, 2:7] = slope[2:7, 2] = slope[2:7, 6] = 40.0
    field = walkback(prepare_terrain(terrain_grid(np.zeros((9, 9)), slope_deg=slope), WalkModel()), [(4, 4)])
    assert math.isinf(field.time_s[0, 0])
    assert field.next_hop[0, 0] == -1
    assert math.isfinite(field.time_s[3, 5])


def test_shelter_on_banned_cell_is_rejected():
    terrain = prepare_terrain(terrain_grid(np.zeros((2, 2)), slope_deg=40.0), WalkModel())
    with pytest.raises(ValueError, match="shelter"):
        walkback(terrain, [(0, 0)])


def test_risk_adjusted_time_adds_path_and_model_uncertainty():
    field = WalkbackField(
        time_s=np.array([[0.0, 100.0]]),
        var_s2=np.array([[0.0, 25.0]]),
        energy_per_kg_j=np.zeros((1, 2)),
        distance_m=np.array([[0.0, 50.0]]),
        next_hop=np.array([[-1, 0]]),
    )
    # 100 + 1.645·sqrt(25 + (0.2·100)²)
    np.testing.assert_allclose(field.time_eps_s(z=1.645, sigma_theta=0.2), [[0.0, 133.91254377070527]], rtol=1e-12)


def test_consumables_on_one_flat_edge_and_affine_theta_scaling():
    field = walkback(prepare_terrain(terrain_grid(np.zeros((1, 2))), WalkModel()), [(0, 0)])
    base = field.consumables(CREW, SuitModel(), WalkModel(), risk=False)
    # D010: suit energy = 335·0.0134·W·4 m on the 4 m edge (old constant-power values reproduced
    # by the same derivation before the change).
    assert field.distance_m[0, 1] == pytest.approx(4.0, rel=1e-12)
    assert base.o2_kg[0, 1] == pytest.approx(0.00013535259192976265, rel=1e-12)
    assert base.water_kg[0, 1] == pytest.approx(0.0006215170037591143, rel=1e-12)
    assert base.battery_wh[0, 1] == pytest.approx(0.10379170109752789, rel=1e-12)
    assert base.co2_kg[0, 1] == pytest.approx(0.00015823343095219057, rel=1e-12)
    assert base.o2_kg[0, 0] == 0.0
    heavy = field.consumables(replace(CREW, theta=1.2), SuitModel(), WalkModel(), risk=False)
    assert heavy.o2_kg[0, 1] == pytest.approx(0.0001445469147601596, rel=1e-12)
    # Suit cost is not scaled by theta, so the field is affine, not linear, in theta.
    assert heavy.o2_kg[0, 1] < 1.2 * base.o2_kg[0, 1]


def test_risk_adjusted_consumables_use_the_time_risk_factor():
    field = walkback(prepare_terrain(terrain_grid(np.zeros((1, 2))), WalkModel()), [(0, 0)])
    base = field.consumables(CREW, SuitModel(), WalkModel(), risk=False)
    risky = field.consumables(CREW, SuitModel(), WalkModel(), risk=True, z=1.645, sigma_theta=0.2)
    # Zero path variance: factor = 1 + 1.645·0.2.
    assert risky.o2_kg[0, 1] == pytest.approx(1.329 * base.o2_kg[0, 1], rel=1e-12)
    assert risky.o2_kg[0, 0] == 0.0


def test_leg_cost_is_directional_on_inclined_plane():
    terrain = inclined_plane()
    assert leg_cost(terrain, (20, 10), (20, 20)).time_s == pytest.approx(65.86373385461116, rel=1e-9)
    assert leg_cost(terrain, (20, 30), (20, 20)).time_s == pytest.approx(46.41338879174768, rel=1e-9)
    assert leg_cost(terrain, (20, 20), (20, 20)).time_s == 0.0


def test_components_split_cells_behind_a_banned_ring():
    slope = np.zeros((9, 9))
    slope[2, 2:7] = slope[6, 2:7] = slope[2:7, 2] = slope[2:7, 6] = 40.0
    labels = walkable_components(prepare_terrain(terrain_grid(np.zeros((9, 9)), slope_deg=slope), WalkModel()))
    inside, outside = labels[4, 4], labels[0, 0]
    assert inside >= 0 and outside >= 0 and inside != outside
    assert np.all(labels[3:6, 3:6] == inside)
    assert labels[2, 2] == -1  # banned cells belong to no component


def test_components_follow_edge_rules_not_cell_adjacency():
    slope = np.zeros((2, 2))
    slope[0, 1] = slope[1, 0] = 40.0  # free cells touch only at a banned corner
    labels = walkable_components(prepare_terrain(terrain_grid(np.zeros((2, 2)), slope_deg=slope), WalkModel()))
    assert labels[0, 0] >= 0 and labels[1, 1] >= 0
    assert labels[0, 0] != labels[1, 1]


@settings(max_examples=30, deadline=None)
@given(st.integers(2, 7), st.integers(2, 7), st.integers(0, 2**32 - 1))
def test_component_of_a_shelter_is_exactly_its_reachable_set(height, width, seed):
    rng = np.random.default_rng(seed)
    slope = rng.uniform(0.0, 32.0, (height, width))
    slope[0, 0] = 0.0
    terrain = prepare_terrain(
        terrain_grid(rng.uniform(-1.0, 1.0, (height, width)), 4.0, slope_deg=slope), WalkModel()
    )
    labels = walkable_components(terrain)
    reachable = np.isfinite(walkback(terrain, [(0, 0)]).time_s)
    np.testing.assert_array_equal(labels == labels[0, 0], reachable)


def test_leg_cost_is_none_when_goal_unreachable():
    slope = np.zeros((9, 9))
    slope[2, 2:7] = slope[6, 2:7] = slope[2:7, 2] = slope[2:7, 6] = 40.0
    terrain = prepare_terrain(terrain_grid(np.zeros((9, 9)), slope_deg=slope), WalkModel())
    assert leg_cost(terrain, (0, 0), (4, 4)) is None


def test_leg_and_return_paths_follow_the_optimal_walks():
    from redline_core.walkback import leg_cost, leg_path, return_path

    terrain = prepare_terrain(terrain_grid(np.zeros((12, 12))), WalkModel())
    path = leg_path(terrain, (2, 2), (2, 9))
    assert path[0] == (2, 2) and path[-1] == (2, 9)
    steps = list(zip(path, path[1:]))
    total = sum(edge_cost(terrain, a, (b[0] - a[0], b[1] - a[1])).time_s for a, b in steps)
    assert total == pytest.approx(leg_cost(terrain, (2, 2), (2, 9)).time_s, rel=1e-12)
    field = walkback(terrain, [(0, 0)])
    back = return_path(field, (7, 5))
    assert back[0] == (7, 5) and back[-1] == (0, 0)
    banned = terrain_grid(np.zeros((5, 5)), slope_deg=0.0)
    banned.layers["slope_deg"][:, 2] = 40.0
    split = prepare_terrain(banned, WalkModel())
    assert leg_path(split, (0, 0), (0, 4)) is None
    assert return_path(walkback(split, [(0, 0)]), (0, 4)) is None
