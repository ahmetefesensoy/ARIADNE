"""Bayesian science value of EVA stations (proje.md §7.10; D011).

Hypotheses H with prior P(H) live in ``config/science_<site>.yaml``. Each station has a
science class (for BXW: ``ridge`` or ``hollow``) and returns a binary outcome (the class
signature is seen or not). The observation model is p(seen | H, class).

The value of a *set* of stations is their joint expected information gain

    EIG(S) = H(P) − Σ_o p(o) · H(P | o),   o ∈ {0,1}^|S|,

computed exactly by enumerating outcomes (|S| ≤ 14). Joint EIG is not additive: a second
station of the same class teaches less than the first, so routes are not rewarded for
redundant stops. Values are in bits. All numbers are SCENARIO assumptions.
"""
from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .params import PROVENANCE_STATUSES

MAX_JOINT_STATIONS = 14


@dataclass(frozen=True, eq=False)
class ScienceModel:
    site_id: str
    question: str
    hypotheses: tuple[str, ...]
    prior: np.ndarray  # (H,)
    p_seen: dict[str, np.ndarray]  # class -> (H,) probability of a positive outcome

    def __post_init__(self) -> None:
        prior = np.asarray(self.prior, dtype=float)
        if prior.shape != (len(self.hypotheses),) or not np.all(prior > 0) or not math.isclose(prior.sum(), 1.0):
            raise ValueError("prior must be positive, one value per hypothesis, summing to 1")
        for name, p in self.p_seen.items():
            p = np.asarray(p, dtype=float)
            if p.shape != prior.shape or not np.all((p > 0) & (p < 1)):
                raise ValueError(f"p_seen[{name!r}] must be one probability in (0, 1) per hypothesis")


def load_science(path: Path | str) -> ScienceModel:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if data.get("provenance_status") not in PROVENANCE_STATUSES:
        raise ValueError(f"{path}: provenance_status must be one of {PROVENANCE_STATUSES}")
    unknown = set(data) - {"provenance_status", "note", "site_id", "question", "hypotheses", "observation",
                           "sources"}
    if unknown:
        raise ValueError(f"{path}: unknown keys {sorted(unknown)}")
    hyps = data["hypotheses"]
    names = tuple(h["id"] for h in hyps)
    prior = np.array([float(h["prior"]) for h in hyps])
    p_seen = {}
    for cls, table in data["observation"].items():
        if set(table) != set(names):
            raise ValueError(f"{path}: observation[{cls}] must give p_seen for every hypothesis {names}")
        p_seen[str(cls)] = np.array([float(table[h]) for h in names])
    return ScienceModel(str(data["site_id"]), str(data.get("question", "")), names, prior, p_seen)


def entropy_bits(p: np.ndarray) -> float:
    p = np.asarray(p, dtype=float)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def posterior(model: ScienceModel, prior: np.ndarray, classes: Sequence[str],
              outcomes: Sequence[bool]) -> np.ndarray:
    if len(classes) != len(outcomes):
        raise ValueError("one outcome per class")
    post = np.asarray(prior, dtype=float).copy()
    for cls, seen in zip(classes, outcomes):
        p = model.p_seen[cls]
        post *= p if seen else (1.0 - p)
    return post / post.sum()


def joint_eig_bits(model: ScienceModel, prior: np.ndarray, classes: Sequence[str]) -> float:
    """Exact expected information gain (bits) of observing all `classes` together."""
    classes = list(classes)
    if not classes:
        return 0.0
    if len(classes) > MAX_JOINT_STATIONS:
        raise ValueError(f"joint EIG is exact up to {MAX_JOINT_STATIONS} stations")
    for cls in classes:
        if cls not in model.p_seen:
            raise ValueError(f"no observation model for station class {cls!r}")
    prior = np.asarray(prior, dtype=float)
    p = np.stack([model.p_seen[c] for c in classes])  # (n, H)
    expected = 0.0
    for outcome in itertools.product((True, False), repeat=len(classes)):
        like = np.prod(np.where(np.array(outcome)[:, None], p, 1.0 - p), axis=0)  # (H,)
        joint = like * prior
        evidence = joint.sum()
        if evidence > 0:
            expected += evidence * entropy_bits(joint / evidence)
    return entropy_bits(prior) - expected
