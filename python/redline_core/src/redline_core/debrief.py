"""Debrief grade computed only from run records (council 2026-11-15; proje.md §16 debrief).

Axes are reported separately so a trade-off is never hidden:
- safety: worst of the rule-violation letter (CAUTION → B, WARNING → C, EMERGENCY → F; INFO ignored)
  and the minimum return margin over the run (below the C threshold, i.e. a reserve breach → F);
- science: information gained about the site question, H(prior) − H(posterior) in bits
  (``science_value``), from the posterior the run's measurements produced;
- samples: RECORDED (chain closed) → A, only acquired/stowed → B, none → C (not in the overall).
The overall letter is the worse of safety and science, so safety caps it lexicographically. The
thresholds are SCENARIO game-design choices, not NASA criteria. No record, no credit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from redline_core.science_value import entropy_bits

ORDER = ("A", "B", "C", "D", "F")
SEVERITY_LETTER = {0: "A", 1: "B", 2: "C", 3: "F"}  # Alert INFO, CAUTION, WARNING, EMERGENCY
IN_PROGRESS = ("SELECTED", "REACH_OK", "PRE_POSITIONED", "READY", "ACQUIRING", "ACQUIRED", "STOWED")


@dataclass(frozen=True)
class Violation:
    record_id: str
    rule_id: str
    severity: int


@dataclass(frozen=True)
class SampleOutcome:
    sample_id: str
    state: str  # SampleRecord state name


@dataclass(frozen=True)
class Thresholds:
    margin_min: dict  # {"A": .., "B": .., "C": ..} minimum return margin, minutes
    bits: dict  # {"A": .., "B": .., "C": ..} information gained, bits


def _worse(*letters: str) -> str:
    return max(letters, key=ORDER.index)


def _step(value: float, table: dict, below: str) -> str:
    for letter in ("A", "B", "C"):
        if value >= table[letter]:
            return letter
    return below


def grade(*, violations, min_margin_min: float, prior, posterior, samples, thresholds: Thresholds) -> dict:
    if not math.isfinite(min_margin_min):
        raise ValueError("min_margin_min must be finite (a run without margin records cannot be graded)")
    prior, posterior = np.asarray(prior, dtype=float), np.asarray(posterior, dtype=float)
    if prior.shape != posterior.shape or not np.isclose(prior.sum(), 1.0) or not np.isclose(posterior.sum(), 1.0):
        raise ValueError("prior and posterior must be distributions over the same hypotheses")
    counted = []
    for v in violations:
        if v.severity not in SEVERITY_LETTER:
            raise ValueError(f"unknown severity {v.severity} for {v.record_id}")
        if v.severity > 0:
            counted.append(v)
    rule_letter = _worse("A", *(SEVERITY_LETTER[v.severity] for v in counted))
    margin_letter = _step(min_margin_min, thresholds.margin_min, "F")
    safety = {"letter": _worse(rule_letter, margin_letter), "min_margin_min": float(min_margin_min),
              "violations": [{"rule_id": v.rule_id, "severity": v.severity} for v in counted],
              "evidence": [v.record_id for v in counted]}
    bits = max(entropy_bits(prior) - entropy_bits(posterior), 0.0)
    science = {"letter": _step(bits, thresholds.bits, "D"), "bits": bits,
               "posterior": [float(p) for p in posterior]}
    recorded = [s.sample_id for s in samples if s.state == "RECORDED"]
    failed = [s.sample_id for s in samples if s.state == "FAILED"]
    progress = [s.sample_id for s in samples if s.state in IN_PROGRESS]
    sample_letter = "A" if recorded else "B" if progress else "C"
    return {"overall": _worse(safety["letter"], science["letter"]), "safety": safety, "science": science,
            "samples": {"letter": sample_letter, "recorded": recorded, "failed": failed, "in_progress": progress},
            "status": "SCENARIO thresholds over run records"}
