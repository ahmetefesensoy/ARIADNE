"""Flight-rule trackers on mission time (proje.md §12, §8.5; D012).

Pure state machines fed by the rule monitor; times are PET seconds.

- FR-04: after the rising edge of a SEP alarm the mission must be in shelter mode within
  ``window_s``. One result per alarm: ``satisfied`` (with latency) or ``violated``.
- FR-01: the crew's return margin (margin_now) must stay ≥ 0; one event per crossing.
- FR-12: at the dusk limit (sunset − T_dusk) every crew member must be in shelter (D014).
- FR-05: buddy distance and terrain line of sight, with a grace period (D015).
- SUIT_LEAK: reported O₂ rate above the metabolic model for a hold time (S2).
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass
class Fr04Tracker:
    window_s: float = 30.0
    alarm_pet_s: float | None = None
    latency_s: float | None = None
    violated: bool = False
    history: list = field(default_factory=list)
    _alert: bool = False

    def update(self, pet_s: float, alert: bool, shelter_mode: bool) -> str | None:
        event = None
        if alert and not self._alert:
            self.alarm_pet_s, self.latency_s, self.violated = pet_s, None, False
        self._alert = alert
        if self.alarm_pet_s is None or self.latency_s is not None:
            return None
        elapsed = pet_s - self.alarm_pet_s
        if shelter_mode:
            self.latency_s = max(elapsed, 0.0)
            event = "satisfied" if not self.violated else "late"
        elif elapsed > self.window_s and not self.violated:
            self.violated = True
            event = "violated"
        if event:
            self.history.append((event, self.alarm_pet_s, pet_s))
        return event


@dataclass
class Fr01Tracker:
    below: bool = False

    def update(self, margin_now_min: float) -> str | None:
        if not math.isfinite(margin_now_min):
            now_below = margin_now_min == -math.inf  # NaN: unknown position, no event
            if math.isnan(margin_now_min):
                return None
        else:
            now_below = margin_now_min < 0.0
        if now_below and not self.below:
            self.below = True
            return "violated"
        if not now_below and self.below:
            self.below = False
            return "cleared"
        return None


@dataclass
class Fr12Tracker:
    """FR-12 on the daylight budget b = (t_sunset − T_dusk) − t_now (solar.daylight_budget_s).

    b ≤ 0 means the dusk limit has passed; −inf means the Sun is below the horizon. One event
    per change: ``satisfied`` when the limit is reached with everyone inside, ``violated`` when
    someone is outside at or after it, ``cleared`` when the crew is back inside (or a new day's
    budget opens). NaN (outside the sun table) is unknown and gives no event.
    """
    violated: bool = False
    _past: bool = False

    def update(self, budget_s: float, outside: Sequence[str]) -> str | None:
        if math.isnan(budget_s):
            return None
        past = budget_s <= 0.0
        event = None
        if self.violated:
            if not (past and outside):
                self.violated, event = False, "cleared"
        elif past and outside:
            self.violated, event = True, "violated"
        elif past and not self._past:
            event = "satisfied"
        self._past = past
        return event


@dataclass
class Fr05Tracker:
    """FR-05 buddy rule (proje.md §12): distance ≤ max and terrain line of sight; CAUTION at the
    first violation, WARNING when it lasts ``grace_s`` (PET), cleared when both hold again.

    Line of sight uses hysteresis on the signed clearance (los.sight_clearance): it is lost below
    −hysteresis_m and regained above +hysteresis_m, so 4 m DTM noise does not make it flap.
    The distance limit has its own band: apart above ``max_distance_m``, together again only at or
    below ``max_distance_m − distance_hysteresis_m`` (S0b on BXW flapped at 104 m without it).
    NaN distance or clearance (no position, no terrain) gives no event.
    """
    max_distance_m: float = 100.0
    grace_s: float = 60.0
    hysteresis_m: float = 0.5
    distance_hysteresis_m: float = 0.0
    violated_since_s: float | None = None
    warned: bool = False
    _visible: bool = True
    _far: bool = False

    def update(self, pet_s: float, distance_m: float, clearance_m: float) -> str | None:
        if not (math.isfinite(distance_m) and math.isfinite(clearance_m)):
            return None
        if self._visible and clearance_m < -self.hysteresis_m:
            self._visible = False
        elif not self._visible and clearance_m > self.hysteresis_m:
            self._visible = True
        if not self._far and distance_m > self.max_distance_m:
            self._far = True
        elif self._far and distance_m <= self.max_distance_m - self.distance_hysteresis_m:
            self._far = False
        bad = self._far or not self._visible
        if bad and self.violated_since_s is None:
            self.violated_since_s, self.warned = pet_s, False
            return "caution"
        if bad and not self.warned and pet_s - self.violated_since_s >= self.grace_s:
            self.warned = True
            return "warning"
        if not bad and self.violated_since_s is not None:
            self.violated_since_s, self.warned = None, False
            return "cleared"
        return None


@dataclass
class LeakTracker:
    """Suit leak from telemetry (proje.md §8.7 SUIT_LEAK, §16 S2; D015 leak factor).

    ``factor`` is the reported O₂ rate over the rate the metabolic model expects
    (field_model.leak_factor). ``detected`` once it stays ≥ ``factor_on`` for ``hold_s`` (PET);
    ``cleared`` only below ``factor_off`` (hysteresis). A missing reading (NaN) restarts the hold and
    never clears. Thresholds are SCENARIO (rules.yaml).
    """
    factor_on: float = 1.5
    factor_off: float = 1.2
    hold_s: float = 30.0
    detected: bool = False
    detected_pet_s: float | None = None
    _high_since_s: float | None = None

    def __post_init__(self) -> None:
        if not (1.0 <= self.factor_off < self.factor_on) or self.hold_s < 0:
            raise ValueError("need 1 <= factor_off < factor_on and hold_s >= 0")

    def update(self, pet_s: float, factor: float) -> str | None:
        if not math.isfinite(factor):
            self._high_since_s = None
            return None
        if self.detected:
            if factor < self.factor_off:
                self.detected, self._high_since_s = False, None
                return "cleared"
            return None
        if factor < self.factor_on:
            self._high_since_s = None
            return None
        if self._high_since_s is None:
            self._high_since_s = pet_s
        if pet_s - self._high_since_s >= self.hold_s:
            self.detected, self.detected_pet_s = True, pet_s
            return "detected"
        return None
