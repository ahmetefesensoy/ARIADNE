"""Cell knowledge node (proje.md §8.3 `cell_store`; D009).

- Loads the orbital planning layers (``planning_grid`` npz + sidecar, SHA-256
  checked) into a :class:`redline_core.cells.CellStore`.
- ``/redline/evidence`` (EvidenceRecord, frame ``map``): a record carrying a
  ``cell_observation`` (D009) updates the cells it covers and is published as a
  ``/redline/cells/delta`` event (CellDelta) with exactly those cells.
- ``/redline/query_cell`` (QueryCell): the cell containing a map point, with
  every EvidenceRecord attached to it.
- ``/redline/cells/known`` (latched CellDelta, D015): every cell holding knowledge. Published at
  most every ``known_period_s`` (default 0.5 s, steady clock) when something changed, so the
  last snapshot is always complete. A snapshot per observation made the traffic quadratic: on
  BXW S4 (1420 scout observations) mission_manager fell behind and lost deltas.

All logic lives in redline_core; this node converts messages only.
"""
from __future__ import annotations

import math

import numpy as np
import rclpy
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_updater import Updater
from rclpy.clock import Clock as RclClock
from rclpy.clock import ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from redline_core.cost_human import UNOBSERVED
from redline_core.cells import CellStore, parse_observation
from redline_core.params import load_models
from redline_core.planning import load_planning_grid
from redline_msgs.msg import CellDelta, CellState, EvidenceRecord
from redline_msgs.srv import QueryCell

EVIDENCE_TOPIC = "/redline/evidence"
DELTA_TOPIC = "/redline/cells/delta"
# D015: every cell that holds knowledge (observed or blocked), latched for nodes that join late.
KNOWN_TOPIC = "/redline/cells/known"
QUERY_SERVICE = "/redline/query_cell"
EVENT_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
KNOWN_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)


def cell_message(view) -> CellState:
    message = CellState()
    message.ix, message.iy = view.ix, view.iy
    message.state = view.state
    message.elevation_m = view.elevation_m
    message.slope_deg = view.slope_deg
    message.slope_sigma_deg = view.slope_sigma_deg
    message.rock_density_per_m2 = view.rock_density_per_m2
    message.speed_factor = view.speed_factor
    message.provenance_status = view.provenance_status
    message.evidence_id = view.evidence_id
    return message


class CellStoreNode(Node):
    def __init__(self, **kwargs):
        super().__init__("cell_store", **kwargs)
        grid_path = str(self.declare_parameter("planning_grid", "").value)
        suit_file = str(self.declare_parameter("suit_file", "").value)
        self.site_id = str(self.declare_parameter("site_id", "").value)
        known_period_s = float(self.declare_parameter("known_period_s", 0.5).value)
        if not (math.isfinite(known_period_s) and known_period_s > 0.0):
            raise ValueError("known_period_s must be positive")
        if not (grid_path and suit_file and self.site_id):
            raise ValueError("planning_grid, suit_file and site_id parameters are required")
        grid, self.grid_meta = load_planning_grid(grid_path)
        site = self.grid_meta.get("provenance", {}).get("site_id")
        if site is not None and site != self.site_id:
            raise ValueError(f"planning grid is for site {site!r}, node is configured for {self.site_id!r}")
        walk, _ = load_models(suit_file)
        self.store = CellStore(grid, walk)
        self.records: dict[str, EvidenceRecord] = {}
        self.counts = {"evidence": 0, "observations": 0, "ignored": 0, "rejected": 0, "deltas": 0, "queries": 0,
                       "snapshots": 0}
        self._known_dirty = False

        self._delta = self.create_publisher(CellDelta, DELTA_TOPIC, EVENT_QOS)
        self._known = self.create_publisher(CellDelta, KNOWN_TOPIC, KNOWN_QOS)
        self.create_subscription(EvidenceRecord, EVIDENCE_TOPIC, self._on_evidence, EVENT_QOS)
        self.create_service(QueryCell, QUERY_SERVICE, self._on_query)
        self.create_timer(known_period_s, self._flush_known, clock=RclClock(clock_type=ClockType.STEADY_TIME))
        self._diagnostics = Updater(self)
        self._diagnostics.setHardwareID(f"cells_{self.site_id}")
        self._diagnostics.add("cell_store", self._diagnose)
        self.get_logger().info(
            f"{grid.height}x{grid.width} cells at {grid.resolution_m} m, npz sha256 {self.grid_meta['npz_sha256'][:12]}")

    def _on_evidence(self, record: EvidenceRecord) -> None:
        self.counts["evidence"] += 1
        position = record.pose.pose.position
        try:
            if record.header.frame_id != "map":
                raise ValueError(f"frame {record.header.frame_id!r} is not map")
            observation = parse_observation(record.evidence_id, position.x, position.y, record.summary_json,
                                            record.provenance.status)
        except ValueError as error:
            self.counts["rejected"] += 1
            self.get_logger().warning(f"evidence {record.evidence_id!r} rejected: {error}")
            return
        if observation is None:
            self.counts["ignored"] += 1
            return
        cells = self.store.apply(observation)
        if not cells:
            self.counts["ignored"] += 1  # repeated evidence id
            return
        self.records[record.evidence_id] = record
        self.counts["observations"] += 1
        self._publish_delta(cells)
        self._known_dirty = True

    def _flush_known(self) -> None:
        if not self._known_dirty:
            return
        self._known_dirty = False
        known = np.argwhere((self.store.state != UNOBSERVED) | self.store.blocked)
        self._publish_delta([tuple(int(v) for v in c) for c in known], self._known)
        self.counts["snapshots"] += 1

    def _publish_delta(self, cells, publisher=None) -> None:
        grid = self.store.grid
        message = CellDelta()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "map"
        message.site_id = self.site_id
        message.resolution_m = float(grid.resolution_m)
        message.origin.x, message.origin.y = (float(v) for v in grid.origin_xy)
        message.cells = [cell_message(self.store.view(iy, ix)) for iy, ix in cells]
        if publisher is not None:
            publisher.publish(message)
            return
        self._delta.publish(message)
        self.counts["deltas"] += 1

    def _on_query(self, request: QueryCell.Request, response: QueryCell.Response) -> QueryCell.Response:
        self.counts["queries"] += 1
        point = request.point
        response.found = False
        if request.site_id != self.site_id or not (math.isfinite(point.x) and math.isfinite(point.y)):
            return response
        result = self.store.query(point.x, point.y)
        if result is None:
            return response
        view, evidence_ids = result
        response.found = True
        response.cell = cell_message(view)
        response.evidence = [self.records[e] for e in evidence_ids if e in self.records]
        return response

    def _diagnose(self, status):
        level = DiagnosticStatus.WARN if self.counts["rejected"] else DiagnosticStatus.OK
        status.summary(level, f"{self.counts['observations']} observations applied")
        for key, value in self.counts.items():
            status.add(key, str(value))
        status.add("npz_sha256", self.grid_meta["npz_sha256"])
        return status


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CellStoreNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
