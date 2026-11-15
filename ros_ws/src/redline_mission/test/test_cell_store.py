"""cell_store over real DDS: evidence → CellDelta event, QueryCell, rejection rules."""
import json
import math
import time

import numpy as np
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter

from redline_core.cells import OBSERVATION_SCHEMA
from redline_core.grid import Grid
from redline_core.planning import save_planning_grid
from redline_mission.cell_store import DELTA_TOPIC, EVENT_QOS, EVIDENCE_TOPIC, QUERY_SERVICE, CellStoreNode
from redline_msgs.msg import CellDelta, CellState, EvidenceRecord, Provenance
from redline_msgs.srv import QueryCell


@pytest.fixture
def files(tmp_path):
    shape = (10, 12)
    z = np.arange(shape[0] * shape[1], dtype=float).reshape(shape)
    layers = {"z_m": z, "slope_deg": np.full(shape, 3.0), "slope_sigma_deg": np.full(shape, 1.0),
              "relief_m": np.zeros(shape), "wall_slope_deg": np.full(shape, 3.0)}
    save_planning_grid(tmp_path / "grid", Grid((-20.0, -8.0), 4.0, 12, 10, layers),
                       {"status": "DERIVED", "site_id": "TST"})
    (tmp_path / "suit.yaml").write_text("provenance_status: SCENARIO\nwalk: {}\nsuit: {}\n")
    return tmp_path


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def record(evidence_id, x, y, observation=None, frame="map", status=Provenance.SIMULATED, extra=None):
    message = EvidenceRecord()
    message.header.frame_id = frame
    message.evidence_id = evidence_id
    message.source = "test_probe"
    message.provenance.status = status
    message.pose.pose.position.x, message.pose.pose.position.y = x, y
    message.pose.pose.orientation.w = 1.0
    summary = dict(extra or {})
    if observation is not None:
        summary["cell_observation"] = {"schema": OBSERVATION_SCHEMA, **observation}
    message.summary_json = json.dumps(summary) if summary else ""
    return message


class Rig:
    def __init__(self, files, site="TST"):
        self.node = CellStoreNode(parameter_overrides=[
            Parameter("planning_grid", value=str(files / "grid.npz")),
            Parameter("suit_file", value=str(files / "suit.yaml")),
            Parameter("site_id", value=site),
        ])
        self.probe = rclpy.create_node("probe")
        self.evidence = self.probe.create_publisher(EvidenceRecord, EVIDENCE_TOPIC, EVENT_QOS)
        self.deltas = []
        self.probe.create_subscription(CellDelta, DELTA_TOPIC, self.deltas.append, EVENT_QOS)
        self.query = self.probe.create_client(QueryCell, QUERY_SERVICE)
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor.add_node(self.probe)

    def spin(self, seconds, until=None):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.01)
            if until is not None and until():
                return True
        return until is None

    def ask(self, x, y, site="TST"):
        request = QueryCell.Request()
        request.site_id = site
        request.point.x, request.point.y = x, y
        future = self.query.call_async(request)
        assert self.spin(5.0, future.done)
        return future.result()

    def close(self):
        self.executor.shutdown()
        self.node.destroy_node()
        self.probe.destroy_node()


def test_observation_publishes_exactly_the_touched_cells_and_query_returns_evidence(ros, files):
    rig = Rig(files)
    try:
        assert rig.spin(3.0, lambda: rig.node.count_publishers(EVIDENCE_TOPIC) > 0 and
                        rig.probe.count_publishers(DELTA_TOPIC) > 0 and rig.query.service_is_ready())
        # Cell (iy=2, ix=5) has its centre at (-20 + 22, -8 + 10) = (2, 2). Radius 4 m: a plus of 5 cells.
        rig.evidence.publish(record("ev-1", 2.0, 2.0, {"state": "DETECTED", "radius_m": 4.0,
                                                      "rock_density_per_m2": 0.03}))
        assert rig.spin(5.0, lambda: len(rig.deltas) == 1)
        delta = rig.deltas[0]
        assert delta.header.frame_id == "map" and delta.site_id == "TST"
        assert (delta.origin.x, delta.origin.y, delta.resolution_m) == (-20.0, -8.0, 4.0)
        cells = {(c.iy, c.ix): c for c in delta.cells}
        assert set(cells) == {(1, 5), (2, 4), (2, 5), (2, 6), (3, 5)}
        centre = cells[(2, 5)]
        assert centre.state == CellState.DETECTED and centre.provenance_status == Provenance.SIMULATED
        assert centre.evidence_id == "ev-1" and centre.speed_factor == 1.0
        assert centre.elevation_m == 29.0 and centre.rock_density_per_m2 == pytest.approx(0.03)

        answer = rig.ask(2.5, 3.9)
        assert answer.found and (answer.cell.iy, answer.cell.ix) == (2, 5)
        assert [e.evidence_id for e in answer.evidence] == ["ev-1"]
        untouched = rig.ask(-19.0, -7.0)
        assert untouched.found and untouched.cell.state == CellState.UNOBSERVED
        assert untouched.cell.provenance_status == Provenance.DERIVED and untouched.evidence == []
        assert math.isnan(untouched.cell.rock_density_per_m2)
        assert not rig.ask(100.0, 0.0).found
        assert not rig.ask(2.0, 2.0, site="BXW").found
    finally:
        rig.close()


def test_repeats_non_observations_and_bad_records_change_nothing(ros, files):
    rig = Rig(files)
    try:
        assert rig.spin(3.0, lambda: rig.node.count_publishers(EVIDENCE_TOPIC) > 0 and
                        rig.probe.count_publishers(DELTA_TOPIC) > 0)
        first = record("ev-1", 2.0, 2.0, {"state": "NOT_DETECTED_LIMITED", "radius_m": 1.0})
        rig.evidence.publish(first)
        assert rig.spin(5.0, lambda: len(rig.deltas) == 1)
        rig.evidence.publish(first)                                                   # repeat
        rig.evidence.publish(record("ev-2", 2.0, 2.0, extra={"apxs": {"SiO2": 45.1}}))  # no observation
        rig.evidence.publish(record("ev-3", 2.0, 2.0, {"state": "DETECTED", "radius_m": 1.0}, frame="odom"))
        rig.evidence.publish(record("ev-4", 2.0, 2.0, {"state": "SEEN", "radius_m": 1.0}))
        assert rig.spin(2.0, lambda: rig.node.counts["evidence"] == 5)
        rig.spin(0.3)
        assert len(rig.deltas) == 1
        assert rig.node.counts["ignored"] == 2 and rig.node.counts["rejected"] == 2
        assert rig.node.store.view(2, 5).state == CellState.NOT_DETECTED_LIMITED
    finally:
        rig.close()


def test_refuses_a_grid_for_another_site(ros, files):
    with pytest.raises(ValueError, match="site"):
        Rig(files, site="BXW")


# --- D015: blocked observations and the cumulative known-cells topic ---------------------------
def test_a_blocked_observation_goes_out_with_zero_speed_and_its_evidence(ros, files):
    from redline_core.cells import OBSERVATION_SCHEMA_V2, delta_updates
    from redline_mission.cell_store import KNOWN_QOS, KNOWN_TOPIC

    rig = Rig(files)
    try:
        message = record("ev-rock", 10.0, 6.0)
        message.summary_json = json.dumps({"cell_observation": {"schema": OBSERVATION_SCHEMA_V2, "state": "DETECTED",
                                                                "radius_m": 1.0, "passable": False}})
        rig.evidence.publish(message)
        assert rig.spin(5.0, lambda: rig.deltas)
        cells = rig.deltas[-1].cells
        assert cells and all(c.speed_factor == 0.0 and c.evidence_id == "ev-rock" for c in cells)
        assert all(blocked for *_, blocked in delta_updates(
            [(c.iy, c.ix, c.state, c.speed_factor, c.evidence_id) for c in cells]))
        late = []  # a node that starts after the observation still gets every known cell
        rig.probe.create_subscription(CellDelta, KNOWN_TOPIC, late.append, KNOWN_QOS)
        assert rig.spin(5.0, lambda: late)
        assert {(c.iy, c.ix) for c in late[-1].cells} >= {(c.iy, c.ix) for c in cells}
    finally:
        rig.close()


def test_a_burst_of_observations_sends_every_delta_but_only_a_few_complete_snapshots(ros, files):
    """S4 on BXW (2026-11-15): a full known-cell snapshot after each of 1420 scout observations made
    the snapshot traffic quadratic; mission_manager fell behind and lost 4 deltas, so the precursor
    gate held. Deltas stay one per observation; the snapshot is rate-limited and always ends complete."""
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

    from redline_mission.cell_store import KNOWN_TOPIC

    rig = Rig(files)
    known = []
    deep = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=200, reliability=ReliabilityPolicy.RELIABLE,
                      durability=DurabilityPolicy.TRANSIENT_LOCAL)
    rig.probe.create_subscription(CellDelta, KNOWN_TOPIC, known.append, deep)
    try:
        assert rig.spin(3.0, lambda: rig.node.count_publishers(EVIDENCE_TOPIC) > 0 and
                        rig.probe.count_publishers(DELTA_TOPIC) > 0)
        ids = [f"ev-{k:02d}" for k in range(40)]
        for k, evidence_id in enumerate(ids):
            rig.evidence.publish(record(evidence_id, -18.0 + 1.1 * k, 2.0 + (k % 5) * 4.0,
                                        {"state": "DETECTED", "radius_m": 4.0}))
        assert rig.spin(10.0, lambda: len(rig.deltas) == 40)
        rig.spin(1.5)  # the last snapshot follows within one period
        assert {c.evidence_id for d in rig.deltas for c in d.cells} == set(ids)
        assert 1 <= len(known) <= 10
        assert {(c.iy, c.ix) for c in known[-1].cells} == {(c.iy, c.ix) for d in rig.deltas for c in d.cells}
    finally:
        rig.close()
