"""Science campaign: stations on terrain targets and the spec's surface tasks (proje.md §9.2 B1–B10).

The campaign file is a SCENARIO design: which spec task runs where, by whom, with which 3D asset,
and why (Turkish and English text for the in-game briefing and tablet). Station positions are not
typed in: a station names a DERIVED terrain target (targets_v1.json, TPI ridge/hollow) and must
claim that target's class; only infrastructure stations (no science class) give their own point.
Tasks name a frozen ROS action (§5, plus the additive CollectSample of D017) or one of the two
non-action task kinds: a crew science note (B10 topic) and a laboratory analysis of a returned
sample (research note SAHA_VE_BILIM_ISTASYONU §4: pH and composition happen in the lab, bound to
the sample's origin). This module validates and resolves; it does not simulate measurements.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

SCHEMA = "redline.science_campaign.v1"
ACTIONS = frozenset({"ContactScience", "RemoteLibs", "MultispectralImage", "NeutronSurvey", "Drill",
                     "CacheSample", "CollectSample", "DeployStation", "ExecuteScout", "SurveyArea",
                     "InspectTarget", "science_note", "lab_analysis"})
ROLES = frozenset({"control", "test", "infrastructure"})
DATA_STATUSES = frozenset({"ARCHIVE", "DERIVED", "SIMULATED", "SCENARIO"})


@dataclass(frozen=True)
class Task:
    task_id: str
    spec: str
    action: str
    actor: str
    asset: str
    data_status: str
    data_note: str
    duration_min: float
    purpose: dict


@dataclass(frozen=True)
class Station:
    station_id: str
    target_id: str | None
    science_class: str | None
    xy_m: tuple[float, float]
    role: str
    name: dict
    purpose: dict
    tasks: tuple[str, ...]


@dataclass(frozen=True)
class Campaign:
    site_id: str
    question: dict
    mission_brief: dict
    tasks: dict[str, Task]
    stations: tuple[Station, ...]


def _text(value, where: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{where}: needs tr and en text")
    for lang in ("tr", "en"):
        if not isinstance(value.get(lang), str) or not value[lang].strip():
            raise ValueError(f"{where}: missing {lang} text")
    return {"tr": value["tr"].strip(), "en": value["en"].strip()}


def load_campaign(path: Path | str, targets_path: Path | str, root: Path | str) -> Campaign:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema must be {SCHEMA}")
    if data.get("provenance_status") != "SCENARIO":
        raise ValueError(f"{path}: a campaign design is SCENARIO")
    targets_doc = json.loads(Path(targets_path).read_text(encoding="utf-8"))
    targets = {t["target_id"]: t for t in targets_doc["targets"]}
    root = Path(root)
    tasks = {}
    for task_id, t in (data.get("tasks") or {}).items():
        where = f"task {task_id}"
        if t.get("action") not in ACTIONS:
            raise ValueError(f"{where}: action {t.get('action')!r} is not a frozen action or task kind")
        asset = str(t.get("asset", ""))
        if not asset or not (root / asset).exists():
            raise ValueError(f"{where}: asset {asset!r} not found")
        status = (t.get("data") or {}).get("status")
        if status not in DATA_STATUSES:
            raise ValueError(f"{where}: data status must be one of {sorted(DATA_STATUSES)}")
        duration = float(t.get("duration_min", 0))
        if not duration > 0:
            raise ValueError(f"{where}: duration_min must be positive")
        tasks[task_id] = Task(task_id, str(t["spec"]), t["action"], str(t["actor"]), asset, status,
                              str((t.get("data") or {}).get("note", "")), duration, _text(t.get("purpose"), where))
    stations = []
    for s in data.get("stations") or []:
        where = f"station {s.get('id')}"
        if s.get("role") not in ROLES:
            raise ValueError(f"{where}: role must be one of {sorted(ROLES)}")
        target_id = s.get("target_id")
        if target_id is not None:
            if target_id not in targets:
                raise ValueError(f"{where}: unknown target {target_id!r}")
            target = targets[target_id]
            if s.get("expected_class") != target["science_class"]:
                raise ValueError(f"{where}: expected class {s.get('expected_class')!r} but the terrain target "
                                 f"is {target['science_class']!r}")
            xy, science_class = tuple(float(v) for v in target["xy_m"]), target["science_class"]
        else:
            if s.get("role") != "infrastructure" or "xy_m" not in s:
                raise ValueError(f"{where}: only infrastructure stations give their own xy_m")
            xy, science_class = tuple(float(v) for v in s["xy_m"]), None
        missing = [t for t in s.get("tasks") or [] if t not in tasks]
        if missing or not s.get("tasks"):
            raise ValueError(f"{where}: unknown task(s) {missing or 'none listed'}")
        stations.append(Station(str(s["id"]), target_id, science_class, xy, s["role"],
                                _text(s.get("name"), where), _text(s.get("purpose"), where), tuple(s["tasks"])))
    return Campaign(str(data["site_id"]), _text(data.get("question"), "question"),
                    _text(data.get("mission_brief"), "mission_brief"), tasks, tuple(stations))
