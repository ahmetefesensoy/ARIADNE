"""Scenario files (proje.md §16; D012): strict loader, run id and the PET → UTC replay map."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .clocks import MissionTime, ReplayMapping

_KEYS = {"id", "site", "seed", "time_scale", "start", "crew", "suit_profile", "replay", "events", "expected",
         "provenance_status", "note", "initial_phase", "truth_file", "plan", "precursor", "crew_trail_s"}
PHASE_NAMES = ("BRIEFING", "PRECURSOR", "TRAVERSE", "STATION_SCIENCE", "RETURN", "CONTINGENCY", "DEBRIEF")
# D015: scheduled events travel as Alert.text = "<human text> | <json payload>".
EVENT_SCHEMA = "redline.scenario_event.v1"
_EVENT_SEPARATOR = " | "


@dataclass(frozen=True)
class ScenarioEvent:
    t_min: float
    type: str
    params: dict


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    site: str
    seed: int
    time_scale: float
    historical_utc: datetime
    pet0_s: float
    crew: tuple[str, ...]
    rad_sols: tuple[int, ...]
    rad_detector: str
    events: tuple[ScenarioEvent, ...]
    expected: tuple[dict, ...]
    initial_phase: str = "TRAVERSE"  # D015: S1 starts mid-EVA; nominal scenarios at BRIEFING
    truth_file: str = ""  # hidden SCENARIO truth, read only by SIMULATED observers (D015)
    plan: dict = field(default_factory=dict)  # PlanEva request for BRIEFING
    precursor: dict = field(default_factory=dict)  # robot precursor before egress (T7)
    crew_trail_s: dict = field(default_factory=dict)  # SIMULATED walk: crew id -> seconds behind the plan

    def replay_mapping(self) -> ReplayMapping:
        """utc = utc0 + (PET − PET0): history advances with mission time (rate 1)."""
        return ReplayMapping(self.historical_utc, MissionTime(self.pet0_s), 1.0)

    def run_id(self, now: datetime | None = None) -> str:
        """proje.md §4.1: YYYYMMDDThhmmssZ-<scenario_id>-<seed>."""
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return f"{now:%Y%m%dT%H%M%SZ}-{self.scenario_id}-{self.seed}"


def encode_event(event: ScenarioEvent, human_text: str) -> str:
    payload = {"schema": EVENT_SCHEMA, "type": event.type, "t_min": event.t_min, "params": event.params}
    return f"{human_text}{_EVENT_SEPARATOR}{json.dumps(payload, sort_keys=True)}"


def parse_event(text: str) -> ScenarioEvent | None:
    """The event in an Alert text written by encode_event; None for text without a payload."""
    if _EVENT_SEPARATOR not in text:
        return None
    raw = text.rsplit(_EVENT_SEPARATOR, 1)[1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"scenario event payload is not JSON ({error})") from None
    if not isinstance(payload, dict) or payload.get("schema") != EVENT_SCHEMA:
        raise ValueError(f"scenario event payload schema must be {EVENT_SCHEMA!r}")
    if not isinstance(payload.get("type"), str) or not payload["type"]:
        raise ValueError("scenario event needs a type")
    params = payload.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("scenario event params must be a mapping")
    return ScenarioEvent(float(payload["t_min"]), payload["type"], dict(params))


def load_scenario(path: Path | str) -> Scenario:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    unknown = set(data) - _KEYS
    if unknown:
        raise ValueError(f"{path}: unknown keys {sorted(unknown)}")
    start = data["start"]
    utc = datetime.fromisoformat(str(start["historical_utc"]).replace("Z", "+00:00"))
    if utc.tzinfo is None:
        raise ValueError(f"{path}: start.historical_utc needs a UTC offset")
    rad = (data.get("replay") or {}).get("rad") or {}
    detector = str(rad.get("detector", "B"))
    if detector not in ("B", "E"):
        raise ValueError(f"{path}: replay.rad.detector must be B or E")
    scale = float(data.get("time_scale", 1.0))
    if not (math.isfinite(scale) and scale > 0):
        raise ValueError(f"{path}: time_scale must be > 0")
    events = tuple(ScenarioEvent(float(e["t_min"]), str(e["type"]), dict(e.get("params") or {}))
                   for e in data.get("events") or [])
    initial = str(data.get("initial_phase", "TRAVERSE"))
    if initial not in PHASE_NAMES:
        raise ValueError(f"{path}: initial_phase must be one of {PHASE_NAMES}")
    for key in ("plan", "precursor", "crew_trail_s"):
        if not isinstance(data.get(key) or {}, dict):
            raise ValueError(f"{path}: {key} must be a mapping")
    crew = tuple(data.get("crew") or ())
    trail = {str(k): float(v) for k, v in (data.get("crew_trail_s") or {}).items()}
    if any(k not in crew or not (math.isfinite(v) and v >= 0) for k, v in trail.items()):
        raise ValueError(f"{path}: crew_trail_s must map scenario crew ids to seconds >= 0")
    return Scenario(str(data["id"]), str(data["site"]), int(data["seed"]), scale, utc,
                    60.0 * float(start.get("pet_min", 0.0)), tuple(data.get("crew") or ()),
                    tuple(int(s) for s in rad.get("sols", ())), detector,
                    tuple(sorted(events, key=lambda e: e.t_min)), tuple(data.get("expected") or ()),
                    initial, str(data.get("truth_file") or ""), dict(data.get("plan") or {}),
                    dict(data.get("precursor") or {}), trail)
