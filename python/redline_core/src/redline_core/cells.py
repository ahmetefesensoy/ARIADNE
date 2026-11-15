"""Cell knowledge store behind the `cell_store` node (proje.md §8.3, CellState.msg).

Orbital layers give every cell its terrain values and the UNOBSERVED state.
Robot or crew observations arrive as EvidenceRecords. The spec does not define
how a record names the cells it observed, so D009 fixes a versioned contract in
``EvidenceRecord.summary_json``::

    {"cell_observation": {"schema": "redline.cell_observation.v1",
                          "state": "DETECTED" | "NOT_DETECTED_LIMITED",
                          "radius_m": 6.0,
                          "rock_density_per_m2": 0.02}}   # optional

The footprint is every cell whose centre lies within `radius_m` of the record's
pose position, plus the cell containing that position. Records without a
``cell_observation`` key are stored nowhere and change nothing.

Knowledge never decreases: DETECTED > NOT_DETECTED_LIMITED > UNOBSERVED. A
weaker later observation keeps the stronger state but its evidence is still
attached. A record with an already applied evidence id is ignored.
`provenance_status` of a cell describes its `state`: DERIVED (orbital only)
until an observation, then that observation's status.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass

import numpy as np

from .cost_human import DETECTED, NOT_DETECTED_LIMITED, UNOBSERVED, WalkModel
from .grid import Grid

OBSERVATION_SCHEMA = "redline.cell_observation.v1"
# D015: v2 adds optional "passable": false — the observer saw an obstacle (rock ≥ D_block);
# the cells become DETECTED and impassable (published with speed_factor 0). Blocked never clears.
OBSERVATION_SCHEMA_V2 = "redline.cell_observation.v2"
_KEYS = {OBSERVATION_SCHEMA: {"schema", "state", "radius_m", "rock_density_per_m2"},
         OBSERVATION_SCHEMA_V2: {"schema", "state", "radius_m", "rock_density_per_m2", "passable"}}
ARCHIVE, DERIVED, SIMULATED, SCENARIO = 0, 1, 2, 3
STATE_CODES = {"DETECTED": DETECTED, "NOT_DETECTED_LIMITED": NOT_DETECTED_LIMITED}
_RANK = np.array([0, 2, 1], dtype=np.int8)  # indexed by state code: UNOBSERVED, DETECTED, LIMITED


@dataclass(frozen=True)
class CellObservation:
    evidence_id: str
    x: float
    y: float
    radius_m: float
    state: int
    provenance_status: int
    rock_density_per_m2: float | None = None
    passable: bool = True


def parse_observation(evidence_id: str, x: float, y: float, summary_json: str,
                      provenance_status: int) -> CellObservation | None:
    """The D009 observation in an EvidenceRecord, None when it carries none."""
    if not summary_json.strip():
        return None
    try:
        summary = json.loads(summary_json)
    except json.JSONDecodeError as error:
        raise ValueError(f"evidence {evidence_id!r}: summary_json is not JSON ({error})") from None
    if not isinstance(summary, dict) or "cell_observation" not in summary:
        return None
    obs = summary["cell_observation"]
    if not isinstance(obs, dict) or obs.get("schema") not in _KEYS:
        raise ValueError(f"evidence {evidence_id!r}: cell_observation.schema must be one of {sorted(_KEYS)}")
    unknown = set(obs) - _KEYS[obs["schema"]]
    if unknown:
        raise ValueError(f"evidence {evidence_id!r}: unknown cell_observation keys {sorted(unknown)}")
    if obs.get("state") not in STATE_CODES:
        raise ValueError(f"evidence {evidence_id!r}: state must be one of {sorted(STATE_CODES)}")
    passable = obs.get("passable", True)
    if not isinstance(passable, bool):
        raise ValueError(f"evidence {evidence_id!r}: passable must be true or false")
    if not passable and obs["state"] != "DETECTED":
        raise ValueError(f"evidence {evidence_id!r}: an obstacle (passable false) must be DETECTED")
    radius = obs.get("radius_m")
    if not isinstance(radius, (int, float)) or not (math.isfinite(radius) and radius > 0):
        raise ValueError(f"evidence {evidence_id!r}: radius_m must be a positive number")
    rock = obs.get("rock_density_per_m2")
    if rock is not None and (not isinstance(rock, (int, float)) or not (math.isfinite(rock) and rock >= 0)):
        raise ValueError(f"evidence {evidence_id!r}: rock_density_per_m2 must be a number >= 0")
    if not evidence_id:
        raise ValueError("an observation needs an evidence_id")
    if provenance_status not in (ARCHIVE, DERIVED, SIMULATED, SCENARIO):
        raise ValueError(f"evidence {evidence_id!r}: unknown provenance status {provenance_status}")
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError(f"evidence {evidence_id!r}: pose position must be finite")
    return CellObservation(evidence_id, float(x), float(y), float(radius), STATE_CODES[obs["state"]],
                           int(provenance_status), None if rock is None else float(rock), passable)


def delta_updates(cells) -> list[tuple[int, int, int, bool]]:
    """(iy, ix, state, speed_factor, evidence_id) from a CellDelta → (iy, ix, state, blocked) (D015).

    Blocked = DETECTED, speed_factor 0 and an evidence id: an obstacle always comes from an
    observation, while a default-initialised CellState (speed_factor 0.0, no evidence) must not
    read as one. Every consumer of /redline/cells/delta uses this so a blocked cell is never read
    as plain DETECTED ground.
    """
    out = []
    for iy, ix, state, speed, evidence_id in cells:
        if int(state) not in (UNOBSERVED, DETECTED, NOT_DETECTED_LIMITED):
            raise ValueError(f"cell {(iy, ix)}: unknown CellState state {state}")
        if not (math.isfinite(speed) and 0.0 <= speed <= 1.0):
            raise ValueError(f"cell {(iy, ix)}: speed_factor must be in [0, 1], got {speed}")
        blocked = int(state) == DETECTED and speed == 0.0 and bool(evidence_id)
        out.append((int(iy), int(ix), int(state), blocked))
    return out


@dataclass(frozen=True)
class CellView:
    iy: int
    ix: int
    state: int
    elevation_m: float
    slope_deg: float
    slope_sigma_deg: float
    rock_density_per_m2: float
    speed_factor: float
    provenance_status: int
    evidence_id: str  # latest evidence attached to the cell, "" if none
    blocked: bool = False  # D015: an obstacle was observed here; speed_factor is 0


class CellStore:
    def __init__(self, grid: Grid, walk: WalkModel, base_status: int = DERIVED):
        self.grid = grid
        self.walk = walk
        shape = (grid.height, grid.width)
        state = np.asarray(grid.layer("state"))
        if not np.isin(state, (UNOBSERVED, DETECTED, NOT_DETECTED_LIMITED)).all():
            raise ValueError("state layer has codes outside CellState")
        self.state = state.astype(np.uint8).copy()
        self.status = np.full(shape, base_status, dtype=np.uint8)
        self.rock = np.full(shape, np.nan)
        self.blocked = np.zeros(shape, dtype=bool)
        self._latest = np.full(shape, -1, dtype=np.int64)
        self._ids: list[str] = []
        self._id_set: set[str] = set()
        self._cell_evidence: dict[int, list[int]] = {}

    def speed_factor(self, state: int) -> float:
        return {UNOBSERVED: self.walk.speed_factor_unobserved,
                NOT_DETECTED_LIMITED: self.walk.speed_factor_limited}.get(int(state), 1.0)

    def footprint(self, x: float, y: float, radius_m: float) -> list[tuple[int, int]]:
        g = self.grid
        x0, y0 = g.origin_xy
        r = g.resolution_m
        lo_x, hi_x = math.floor((x - radius_m - x0) / r), math.floor((x + radius_m - x0) / r)
        lo_y, hi_y = math.floor((y - radius_m - y0) / r), math.floor((y + radius_m - y0) / r)
        cells = set()
        for iy in range(max(lo_y, 0), min(hi_y, g.height - 1) + 1):
            for ix in range(max(lo_x, 0), min(hi_x, g.width - 1) + 1):
                cx, cy = g.cell_center(iy, ix)
                if math.hypot(cx - x, cy - y) <= radius_m:
                    cells.add((iy, ix))
        try:
            cells.add(g.cell_index(x, y))
        except ValueError:
            pass  # the position itself lies outside the grid
        return sorted(cells)

    def apply(self, obs: CellObservation) -> list[tuple[int, int]]:
        """Apply an observation; returns the cells it touched (empty if a repeat)."""
        if obs.evidence_id in self._id_set:
            return []
        cells = self.footprint(obs.x, obs.y, obs.radius_m)
        index = len(self._ids)
        self._ids.append(obs.evidence_id)
        self._id_set.add(obs.evidence_id)
        for iy, ix in cells:
            if _RANK[obs.state] > _RANK[self.state[iy, ix]]:
                self.state[iy, ix] = obs.state
            if not obs.passable:
                self.blocked[iy, ix] = True  # never cleared (D015)
            if obs.rock_density_per_m2 is not None:
                self.rock[iy, ix] = obs.rock_density_per_m2
            self.status[iy, ix] = obs.provenance_status
            self._latest[iy, ix] = index
            self._cell_evidence.setdefault(iy * self.grid.width + ix, []).append(index)
        return cells

    def view(self, iy: int, ix: int) -> CellView:
        layers = self.grid.layers
        latest = int(self._latest[iy, ix])
        return CellView(
            iy=iy, ix=ix, state=int(self.state[iy, ix]),
            elevation_m=float(layers["z_m"][iy, ix]),
            slope_deg=float(layers["slope_deg"][iy, ix]),
            slope_sigma_deg=float(layers["slope_sigma_deg"][iy, ix]),
            rock_density_per_m2=float(self.rock[iy, ix]),
            speed_factor=0.0 if self.blocked[iy, ix] else self.speed_factor(self.state[iy, ix]),
            provenance_status=int(self.status[iy, ix]),
            evidence_id=self._ids[latest] if latest >= 0 else "",
            blocked=bool(self.blocked[iy, ix]),
        )

    def evidence_ids(self, iy: int, ix: int) -> list[str]:
        return [self._ids[i] for i in self._cell_evidence.get(iy * self.grid.width + ix, [])]

    def query(self, x: float, y: float) -> tuple[CellView, list[str]] | None:
        try:
            iy, ix = self.grid.cell_index(x, y)
        except ValueError:
            return None
        return self.view(iy, ix), self.evidence_ids(iy, ix)
