"""Explicit SCENARIO instrument rehearsal, not calibrated NASA measurements.

No robot kinematics live here. This module owns validation, repeatable synthetic
measurements, sample custody, and product persistence for proje.md sections 5/9.
Physical contact/flight/drilling require independent sensor/controller evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import hashlib
import json
import math
from pathlib import Path
import random
import re
from typing import Mapping
import xml.etree.ElementTree as ET

import yaml


SCHEMA = "redline.science.product.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
LIMITATION = ("SIMULATED rehearsal using explicit SCENARIO values and uncalibrated scenario noise; "
              "no NASA assay, physical contact, sensor-derived spectrum, or drilled material is claimed")


def checked_id(value: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError("identifier must be a bounded filename-safe string")
    return value


def finite_point(point) -> tuple[float, float, float]:
    if len(point) != 3 or not all(math.isfinite(float(v)) for v in point):
        raise ValueError("a finite ENU metre point is required")
    return tuple(float(v) for v in point)


@dataclass(frozen=True)
class ScienceTarget:
    target_id: str
    point: tuple[float, float, float]
    composition: dict[str, float]
    sigma_percent: float
    weh_percent: float
    input_ids: tuple[str, ...]
    hardness: float = 0.5


def load_targets(path: str | Path) -> tuple[int, dict[str, ScienceTarget], dict]:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if doc.get("provenance_status") != "SCENARIO" or doc.get("noise_calibration") != "UNCALIBRATED_SCENARIO":
        raise ValueError("this rehearsal backend accepts explicitly uncalibrated SCENARIO targets only")
    targets = {}
    for item in doc.get("targets", []):
        target_id = checked_id(item["id"])
        if target_id in targets:
            raise ValueError("duplicate target id")
        composition = {str(k): float(v) for k, v in item["composition_percent"].items()}
        values = list(composition.values()) + [float(item["sigma_percent"]), float(item["weh_percent"])]
        if not composition or not all(math.isfinite(v) and 0 <= v <= 100 for v in values):
            raise ValueError("invalid scenario chemistry or uncertainty")
        if item["sigma_percent"] <= 0:
            raise ValueError("positive uncertainty required")
        inputs = tuple(str(v) for v in item.get("input_ids", []))
        if not inputs:
            raise ValueError("scenario input ids required")
        hardness = float(item.get("hardness", 0.5))
        if not math.isfinite(hardness) or not 0 <= hardness <= 1:
            raise ValueError("scenario hardness outside [0,1]")
        targets[target_id] = ScienceTarget(target_id, finite_point(item["point_m"]), composition,
                                           float(item["sigma_percent"]), float(item["weh_percent"]), inputs, hardness)
    if not targets:
        raise ValueError("at least one scenario target required")
    return int(doc["seed"]), targets, doc


def readiness_error(*, active: bool, simulated_enabled: bool, physical_mode: bool,
                    pose: tuple | None, age_s: float, target: tuple, max_range_m: float,
                    available_power_w: float, required_power_w: float, max_age_s: float = 2.0) -> str:
    if not active:
        return "instrument lifecycle is not active"
    if physical_mode:
        return "physical backend unavailable: contact/force/kinematic sensor evidence required"
    if not simulated_enabled:
        return "SIMULATED backend is not explicitly enabled"
    if pose is None or not math.isfinite(age_s) or age_s < 0 or age_s > max_age_s:
        return "instrument pose missing or stale"
    try:
        origin, destination = finite_point(pose), finite_point(target)
    except (TypeError, ValueError):
        return "invalid pose or target"
    if not math.isfinite(max_range_m) or max_range_m <= 0:
        return "invalid instrument range"
    if math.dist(origin, destination) > max_range_m:
        return "target outside instrument range"
    if not all(math.isfinite(v) and v >= 0 for v in (available_power_w, required_power_w)):
        return "power state invalid"
    if available_power_w < required_power_w:
        return "insufficient instrument power budget"
    return ""


def synthetic_measurement(target: ScienceTarget, instrument: str, request_id: str, seed: int,
                          integration_s: float = 20.0) -> dict:
    checked_id(request_id)
    if not math.isfinite(integration_s) or not 0 < integration_s <= 3600:
        raise ValueError("integration must be in (0,3600] s")
    digest = hashlib.sha256(f"{seed}:{request_id}:{target.target_id}:{instrument}".encode()).digest()
    generator = random.Random(int.from_bytes(digest[:8], "big"))
    sigma = target.sigma_percent * math.sqrt(20.0 / integration_s)
    if instrument in ("APXS", "LIBS"):
        labels = sorted(target.composition)
        truth = [target.composition[k] for k in labels]
        values = [max(0.0, min(100.0, generator.gauss(v, sigma))) for v in truth]
        unit = "mass_percent_SCENARIO"
    elif instrument == "DAN":
        labels, values, unit = ["WEH"], [max(0.0, min(100.0, generator.gauss(target.weh_percent, sigma)))], "percent_SCENARIO"
    elif instrument in ("DRILL", "SAMPLE"):
        labels, values, unit = ["hardness"], [target.hardness], "scenario_index"
        sigma = 0.0
    elif instrument in ("WEATHER", "DOSIMETER"):
        # This operation only records deployment. No temperature/dose is invented.
        labels, values, unit, sigma = [], [], "deployment_record", 0.0
    else:
        raise ValueError("instrument not supported by the rehearsal model")
    return {"labels": labels, "values": values, "sigma": [sigma] * len(values), "unit": unit,
            "integration_s": integration_s, "noise_calibration": "UNCALIBRATED_SCENARIO", "seed": seed,
            "input_ids": list(target.input_ids), "limitation": LIMITATION}


class SampleState(IntEnum):
    SELECTED = 0
    REACH_OK = 1
    PRE_POSITIONED = 2
    READY = 3
    ACQUIRING = 4
    ACQUIRED = 5
    STOWED = 6
    RECORDED = 7
    FAILED = 8


@dataclass
class Sample:
    sample_id: str
    target_id: str
    origin_point: tuple[float, float, float]
    analysis_point: tuple[float, float, float]
    tool: str
    container_id: str = ""
    state: SampleState = SampleState.SELECTED
    evidence_ids: list[str] = field(default_factory=list)

    def advance(self, state: SampleState) -> None:
        if self.state in (SampleState.FAILED, SampleState.RECORDED):
            raise ValueError("sample custody is terminal")
        if state != SampleState.FAILED and int(state) != int(self.state) + 1:
            raise ValueError("sample custody cannot skip or reverse states")
        if state in (SampleState.STOWED, SampleState.RECORDED) and not self.container_id:
            raise ValueError("a container id is required before stowing")
        self.state = state

    def as_dict(self) -> dict:
        return {"sample_id": self.sample_id, "target_id": self.target_id,
                "origin_point_m": list(self.origin_point), "analysis_point_m": list(self.analysis_point),
                "tool": self.tool, "container_id": self.container_id, "state": int(self.state),
                "state_name": self.state.name, "evidence_ids": list(self.evidence_ids),
                "provenance_status": "SIMULATED", "limitation": LIMITATION}


def phases_for(instrument: str, *, stall: bool = False) -> tuple[str, ...]:
    if instrument == "DRILL":
        return ("SELECTED", "REACH_OK", "PRE_POSITIONED", "READY", "ACQUIRING", *(
            ("STALL", "RETRACT", "REDUCE_FEED", "PERCUSSIVE_RECOVERY") if stall else ()), "ACQUIRED")
    if instrument == "SAMPLE":
        return ("PREPARE_CONTAINER", "STOWED", "RECORDED")
    if instrument == "LIBS":
        return ("TARGET_SELECTION", "POINTING", "RASTER", "INTEGRATING", "WRITE_PRODUCT")
    if instrument == "APXS":
        return ("REACH_CHECK", "PRE_POSITIONED", "CONTACT_REHEARSAL", "INTEGRATING", "WRITE_PRODUCT")
    if instrument == "DAN":
        return ("SELECT_POINT", "STATIONARY_REHEARSAL", "INTEGRATING", "POSTERIOR", "WRITE_PRODUCT")
    return ("POSITION_CHECK", "DEPLOYING", "RECORDING")


def phase_at(phases: tuple[str, ...], elapsed_s: float, duration_s: float) -> tuple[str, float]:
    if not phases or not math.isfinite(duration_s) or duration_s <= 0 or not math.isfinite(elapsed_s):
        raise ValueError("valid phases and duration required")
    fraction = max(0.0, min(1.0, elapsed_s / duration_s))
    return phases[min(len(phases) - 1, int(fraction * len(phases)))], fraction


def polygon_contains(point_xy, polygon) -> bool:
    """Bounded finite ENU polygon; boundary belongs to the requested survey."""
    if not 3 <= len(polygon) <= 64:
        raise ValueError("polygon needs 3..64 points")
    x, y = map(float, point_xy)
    vertices = [(float(v[0]), float(v[1])) for v in polygon]
    if not all(math.isfinite(v) for pair in vertices + [(x, y)] for v in pair):
        raise ValueError("finite polygon coordinates required")
    area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(vertices, vertices[1:] + vertices[:1]))) / 2
    if area < 1e-6:
        raise ValueError("survey polygon has zero area")
    inside = False
    for (ax, ay), (bx, by) in zip(vertices, vertices[1:] + vertices[:1]):
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if abs(cross) <= 1e-8 and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by):
            return True
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


def posterior_grid(points, values, noise_sigma: float, *, length_m: float = 5.0, size: int = 9) -> dict:
    """Small Gaussian-process scenario WEH posterior; supplied observations only."""
    import numpy as np
    if not (1 <= len(points) <= 64 and len(points) == len(values) and 2 <= size <= 33):
        raise ValueError("bounded observations and grid required")
    pts = np.asarray(points, dtype=float)[:, :2]
    val = np.asarray(values, dtype=float)
    if not (np.isfinite(pts).all() and np.isfinite(val).all() and math.isfinite(noise_sigma)
            and noise_sigma > 0 and length_m > 0):
        raise ValueError("finite positive GP parameters required")
    lo, hi = pts.min(axis=0) - 2, pts.max(axis=0) + 2
    resolution = max(float(max(hi - lo)) / (size - 1), 0.5)
    query = np.array([(lo[0] + x * resolution, lo[1] + y * resolution)
                      for y in range(size) for x in range(size)])
    kernel = lambda a, b: np.exp(-np.sum((a[:, None] - b[None, :]) ** 2, axis=2) / (2 * length_m ** 2))
    covariance = kernel(pts, pts) + np.eye(len(pts)) * (noise_sigma ** 2 + 1e-8)
    cross = kernel(query, pts)
    mean = float(val.mean()) + cross @ np.linalg.solve(covariance, val - val.mean())
    variance = np.maximum(0.0, 1 - np.sum(cross * np.linalg.solve(covariance, cross.T).T, axis=1))
    return {"origin_m": lo.tolist(), "resolution_m": resolution, "width": size, "height": size,
            "values": mean.tolist(), "sigma": np.sqrt(variance).tolist(), "unit": "percent_SCENARIO",
            "kernel": "RBF; scenario amplitude=1 percent^2", "status": "SIMULATED"}


class ProductStore:
    def __init__(self, root: str | Path, run_id: str):
        self.run_id = checked_id(run_id)
        self.path = Path(root) / self.run_id
        self.path.mkdir(parents=True, exist_ok=True)

    def reserve_request(self, request_id: str) -> bool:
        checked_id(request_id)
        marker = self.path / ("request-" + hashlib.sha256(request_id.encode()).hexdigest() + ".json")
        try:
            with marker.open("x", encoding="utf-8") as stream:
                json.dump({"request_id": request_id, "run_id": self.run_id}, stream)
        except FileExistsError:
            return False
        return True

    def write(self, *, request_id: str, instrument: str, target: ScienceTarget, measured_utc: str,
              integration_s: float, instrument_point, measurement: Mapping, sample: Sample | None = None) -> dict:
        checked_id(request_id)
        checked_id(instrument)
        origin = finite_point(instrument_point)
        suffix = hashlib.sha256(f"{request_id}:{instrument}:{target.target_id}".encode()).hexdigest()[:16]
        product_id = f"sim-{instrument.lower()}-{self.run_id}-{suffix}"
        evidence_id = f"ev-{self.run_id}-{suffix}"
        payload = {"schema": SCHEMA, "product_id": product_id, "evidence_id": evidence_id,
                   "run_id": self.run_id, "request_id": request_id, "instrument": instrument,
                   "target_id": target.target_id, "target_point_m": list(target.point),
                   "instrument_point_m": list(origin), "measured_utc": measured_utc,
                   "integration_s": integration_s, "provenance_status": "SIMULATED",
                   "input_ids": list(dict.fromkeys([*target.input_ids, *(sample.evidence_ids if sample else [])])),
                   "measurement": dict(measurement), "limitation": LIMITATION}
        if sample is not None:
            payload["sample"] = sample.as_dict()
            payload["sample"]["evidence_ids"] = list(dict.fromkeys([*sample.evidence_ids, evidence_id]))
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
        json_path, xml_path = self.path / f"{product_id}.json", self.path / f"{product_id}.xml"
        if json_path.exists():
            raise ValueError("product id already exists")
        label = ET.Element("Redline_Product_Label", {"style": "PDS4-like; not a validated PDS4 product"})
        for key in ("product_id", "instrument", "target_id", "measured_utc", "integration_s", "provenance_status"):
            ET.SubElement(label, key).text = str(payload[key])
        ET.SubElement(label, "target_point_m").text = json.dumps(payload["target_point_m"])
        ET.SubElement(label, "instrument_point_m").text = json.dumps(payload["instrument_point_m"])
        ET.SubElement(label, "input_ids").text = json.dumps(payload["input_ids"])
        ET.SubElement(label, "limitation").text = LIMITATION
        ET.SubElement(label, "json_sha256").text = hashlib.sha256(raw).hexdigest()
        temporary = json_path.with_suffix(".json.tmp")
        temporary.write_bytes(raw)
        ET.ElementTree(label).write(xml_path, encoding="utf-8", xml_declaration=True)
        temporary.replace(json_path)
        return {**payload, "payload_uri": str(json_path), "sha256": hashlib.sha256(raw).hexdigest()}
