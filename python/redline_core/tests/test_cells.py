"""cell_store core: observation contract, footprint, monotonic knowledge, query (D009)."""
import json
import math

import numpy as np
import pytest

from core_helpers import terrain_grid
from redline_core.cells import (
    DERIVED,
    OBSERVATION_SCHEMA,
    SIMULATED,
    CellObservation,
    CellStore,
    parse_observation,
)
from redline_core.cost_human import DETECTED, NOT_DETECTED_LIMITED, UNOBSERVED, WalkModel


def summary(**obs):
    return json.dumps({"cell_observation": {"schema": OBSERVATION_SCHEMA, **obs}})


def store(shape=(10, 10)):
    grid = terrain_grid(np.arange(shape[0] * shape[1], dtype=float).reshape(shape), 4.0,
                        state=UNOBSERVED, slope_deg=3.0, sigma_deg=1.5)
    return CellStore(grid, WalkModel())


def test_parse_valid_observation_and_records_without_one():
    obs = parse_observation("ev-1", 10.0, 6.0, summary(state="DETECTED", radius_m=5.0,
                                                       rock_density_per_m2=0.02), SIMULATED)
    assert obs == CellObservation("ev-1", 10.0, 6.0, 5.0, DETECTED, SIMULATED, 0.02)
    assert parse_observation("ev-2", 0.0, 0.0, "", SIMULATED) is None
    assert parse_observation("ev-3", 0.0, 0.0, json.dumps({"apxs": 1}), SIMULATED) is None


@pytest.mark.parametrize("text", [
    "{not json",
    json.dumps({"cell_observation": {"schema": "v0", "state": "DETECTED", "radius_m": 1}}),
    summary(state="SEEN", radius_m=1.0),
    summary(state="DETECTED", radius_m=0.0),
    summary(state="DETECTED", radius_m=float("nan")),
    summary(state="DETECTED", radius_m=2.0, rock_density_per_m2=-1.0),
    summary(state="DETECTED", radius_m=2.0, colour="red"),
])
def test_parse_rejects_malformed_observations(text):
    with pytest.raises(ValueError):
        parse_observation("ev-x", 0.0, 0.0, text, SIMULATED)


def test_parse_rejects_bad_status_and_position():
    with pytest.raises(ValueError):
        parse_observation("ev-x", 0.0, 0.0, summary(state="DETECTED", radius_m=1.0), 9)
    with pytest.raises(ValueError):
        parse_observation("ev-x", math.inf, 0.0, summary(state="DETECTED", radius_m=1.0), SIMULATED)
    with pytest.raises(ValueError):
        parse_observation("", 0.0, 0.0, summary(state="DETECTED", radius_m=1.0), SIMULATED)


def test_footprint_is_cells_with_centres_in_the_disk_plus_the_containing_cell():
    s = store()
    # Centre (10, 10) m: cell centres at 2, 6, 10, 14, ... Radius 4 reaches (10±4, 10) and (10, 10±4).
    cells = s.footprint(10.0, 10.0, 4.0)
    assert cells == [(1, 2), (2, 1), (2, 2), (2, 3), (3, 2)]
    # A tiny radius still marks the containing cell.
    assert s.footprint(9.0, 9.0, 0.1) == [(2, 2)]
    # Clipped at the grid edge; a point outside touches only in-grid centres in range.
    assert s.footprint(-1.0, 2.0, 3.5) == [(0, 0)]
    assert s.footprint(-100.0, -100.0, 1.0) == []


def test_apply_sets_state_status_rock_and_evidence():
    s = store()
    obs = CellObservation("ev-1", 10.0, 10.0, 4.0, NOT_DETECTED_LIMITED, SIMULATED, 0.05)
    touched = s.apply(obs)
    assert len(touched) == 5
    view = s.view(2, 2)
    assert view.state == NOT_DETECTED_LIMITED and view.provenance_status == SIMULATED
    assert view.rock_density_per_m2 == 0.05 and view.evidence_id == "ev-1"
    assert view.speed_factor == WalkModel().speed_factor_limited
    assert view.elevation_m == 22.0 and view.slope_deg == 3.0 and view.slope_sigma_deg == 1.5
    untouched = s.view(5, 5)
    assert untouched.state == UNOBSERVED and untouched.provenance_status == DERIVED
    assert math.isnan(untouched.rock_density_per_m2) and untouched.evidence_id == ""
    assert untouched.speed_factor == WalkModel().speed_factor_unobserved


def test_knowledge_never_decreases_but_evidence_is_kept():
    s = store()
    s.apply(CellObservation("ev-1", 10.0, 10.0, 1.0, DETECTED, SIMULATED))
    s.apply(CellObservation("ev-2", 10.0, 10.0, 1.0, NOT_DETECTED_LIMITED, SIMULATED))
    view = s.view(2, 2)
    assert view.state == DETECTED and view.evidence_id == "ev-2"
    assert view.speed_factor == 1.0
    assert s.evidence_ids(2, 2) == ["ev-1", "ev-2"]


def test_repeated_evidence_id_is_ignored():
    s = store()
    obs = CellObservation("ev-1", 10.0, 10.0, 1.0, DETECTED, SIMULATED)
    assert s.apply(obs) == [(2, 2)]
    assert s.apply(obs) == []
    assert s.evidence_ids(2, 2) == ["ev-1"]


def test_query_maps_a_point_to_its_cell():
    s = store()
    s.apply(CellObservation("ev-1", 10.0, 10.0, 1.0, DETECTED, SIMULATED))
    view, evidence = s.query(9.9, 8.1)
    assert (view.iy, view.ix) == (2, 2) and evidence == ["ev-1"]
    assert s.query(-0.1, 0.0) is None and s.query(40.0, 0.0) is None


def test_rejects_unknown_state_codes_in_the_grid():
    grid = terrain_grid(np.zeros((2, 2)), state=7)
    with pytest.raises(ValueError):
        CellStore(grid, WalkModel())


# --- D015: cell_observation v2 (blocked) -------------------------------------------------
from redline_core.cells import OBSERVATION_SCHEMA_V2, delta_updates  # noqa: E402


def summary_v2(**obs):
    return json.dumps({"cell_observation": {"schema": OBSERVATION_SCHEMA_V2, **obs}})


def test_v2_blocked_observation_makes_cells_detected_and_impassable():
    obs = parse_observation("ev-b", 10.0, 6.0, summary_v2(state="DETECTED", radius_m=3.0, passable=False),
                            SIMULATED)
    assert obs.passable is False
    s = store()
    cells = s.apply(obs)
    assert cells and all(s.blocked[c] for c in cells)
    view = s.view(*cells[0])
    assert view.state == DETECTED and view.speed_factor == 0.0 and view.blocked
    assert s.view(9, 9).speed_factor == WalkModel().speed_factor_unobserved and not s.view(9, 9).blocked


def test_v2_defaults_to_passable_and_v1_rejects_the_passable_key():
    obs = parse_observation("ev-p", 1.0, 1.0, summary_v2(state="DETECTED", radius_m=1.0), SIMULATED)
    assert obs.passable is True
    with pytest.raises(ValueError, match="unknown cell_observation keys"):
        parse_observation("ev-q", 1.0, 1.0, summary(state="DETECTED", radius_m=1.0, passable=False), SIMULATED)
    with pytest.raises(ValueError, match="passable"):
        parse_observation("ev-r", 1.0, 1.0, summary_v2(state="DETECTED", radius_m=1.0, passable="no"), SIMULATED)


def test_blocked_is_never_cleared_by_a_later_passable_observation():
    s = store()
    s.apply(parse_observation("ev-1", 10.0, 6.0, summary_v2(state="DETECTED", radius_m=2.0, passable=False),
                              SIMULATED))
    s.apply(parse_observation("ev-2", 10.0, 6.0, summary_v2(state="DETECTED", radius_m=2.0, passable=True),
                              SIMULATED))
    iy, ix = s.grid.cell_index(10.0, 6.0)
    assert s.blocked[iy, ix] and s.view(iy, ix).speed_factor == 0.0
    assert s.evidence_ids(iy, ix) == ["ev-1", "ev-2"]


def test_delta_updates_need_zero_speed_detected_and_evidence_for_blocked():
    updates = delta_updates([(1, 2, DETECTED, 0.0, "ev-1"), (3, 4, NOT_DETECTED_LIMITED, 0.85, "ev-2"),
                             (5, 6, DETECTED, 1.0, "ev-3")])
    assert updates == [(1, 2, DETECTED, True), (3, 4, NOT_DETECTED_LIMITED, False), (5, 6, DETECTED, False)]
    # A default-initialised CellState (speed_factor 0.0, no evidence) is not an obstacle.
    assert delta_updates([(7, 8, DETECTED, 0.0, "")]) == [(7, 8, DETECTED, False)]
    with pytest.raises(ValueError, match="speed_factor"):
        delta_updates([(0, 0, DETECTED, math.nan, "ev")])
    with pytest.raises(ValueError, match="state"):
        delta_updates([(0, 0, 7, 1.0, "ev")])
