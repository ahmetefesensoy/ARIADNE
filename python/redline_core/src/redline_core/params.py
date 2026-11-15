"""Load scenario parameters from config/crew.yaml and config/suit.yaml.

Unknown keys are rejected so a misspelled parameter cannot silently fall back
to its default. Every file must declare its Provenance.status.
"""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import yaml

from .cost_human import CrewMember, SuitModel, WalkModel

PROVENANCE_STATUSES = ("ARCHIVE", "DERIVED", "SIMULATED", "SCENARIO")


def _read(path: Path | str, allowed: set[str]) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    status = data.get("provenance_status")
    if status not in PROVENANCE_STATUSES:
        raise ValueError(f"{path}: provenance_status must be one of {PROVENANCE_STATUSES}, got {status!r}")
    unknown = set(data) - allowed - {"provenance_status", "note"}
    if unknown:
        raise ValueError(f"{path}: unknown top-level keys {sorted(unknown)}")
    return data


def _build(cls, values, where: str, **fixed):
    if not isinstance(values, dict):
        raise ValueError(f"{where}: expected a mapping")
    names = {f.name for f in fields(cls)} - set(fixed)
    unknown = set(values) - names
    if unknown:
        raise ValueError(f"{where}: unknown parameters {sorted(unknown)}")
    converted = {k: (None if v is None else float(v)) for k, v in values.items()}
    return cls(**fixed, **converted)


def load_crew(path: Path | str) -> dict[str, CrewMember]:
    data = _read(path, {"crew"})
    crew = data.get("crew")
    if not isinstance(crew, dict) or not crew:
        raise ValueError(f"{path}: 'crew' must map crew ids to parameters")
    return {str(cid): _build(CrewMember, v, f"{path}: crew {cid}", crew_id=str(cid)) for cid, v in crew.items()}


def load_models(path: Path | str) -> tuple[WalkModel, SuitModel]:
    data = _read(path, {"walk", "suit"})
    walk = _build(WalkModel, data.get("walk") or {}, f"{path}: walk")
    suit = _build(SuitModel, data.get("suit") or {}, f"{path}: suit")
    return walk, suit
