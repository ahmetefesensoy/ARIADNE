"""Solar energetic particle alarm and the shelter flight rule (proje.md §7.12, FR-03/04).

Dose rates are µGy/h as recorded by RAD (proje.md §6.3). Times are seconds on the
replay/mission axis supplied by the caller.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

# Alert.msg severities.
INFO = 0
CAUTION = 1
WARNING = 2
EMERGENCY = 3

SIX_HOURS_S = 6 * 3600.0


@dataclass(frozen=True)
class DetectorState:
    time_s: float
    dose: float
    background: float
    ratio: float
    alert: bool


@dataclass(frozen=True)
class SepStatus:
    alert: bool
    detector: str
    by_detector: Mapping[str, DetectorState]


@dataclass(frozen=True)
class SepDecision:
    severity: int
    recommend_return: bool


def background_median(times_s, dose, now_s: float, window_s: float = SIX_HOURS_S) -> float:
    """Median of readings in [now - window, now); NaN when the window is empty."""
    t = np.asarray(times_s, dtype=float)
    d = np.asarray(dose, dtype=float)
    mask = (t >= now_s - window_s) & (t < now_s) & np.isfinite(d)
    return float(np.median(d[mask])) if mask.any() else math.nan


def evaluate(
    readings: Mapping[str, tuple[np.ndarray, np.ndarray]],
    now_s: float,
    *,
    detector: str = "B",
    factor: float = 1.25,
    window_s: float = SIX_HOURS_S,
) -> SepStatus:
    """Latest reading of each detector against its own background; `detector` decides."""
    if detector not in readings:
        raise ValueError(f"selected detector {detector!r} has no readings")
    states = {}
    for name, (times, values) in readings.items():
        t = np.asarray(times, dtype=float)
        d = np.asarray(values, dtype=float)
        past = np.nonzero(t <= now_s)[0]
        if past.size == 0:
            states[name] = DetectorState(math.nan, math.nan, math.nan, math.nan, False)
            continue
        i = past[np.argmax(t[past])]
        background = background_median(t, d, t[i], window_s)
        ratio = d[i] / background if background > 0 else math.nan
        alert = bool(math.isfinite(ratio) and d[i] >= factor * background)
        states[name] = DetectorState(float(t[i]), float(d[i]), background, float(ratio), alert)
    return SepStatus(states[detector].alert, detector, states)


def shelter_decision(alert: bool, t_shelter_s: float, t_sep_max_s: float = 1200.0) -> SepDecision:
    """At an alarm the crew must be within T_SEP,max of shelter; otherwise EMERGENCY + return."""
    if not alert:
        return SepDecision(INFO, False)
    if not t_shelter_s <= t_sep_max_s:  # NaN/inf (no path) also violates the rule
        return SepDecision(EMERGENCY, True)
    return SepDecision(WARNING, False)
