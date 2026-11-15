"""Crew consumables from observed motion, for `ev_sim` (proje.md §7.2, §8.2).

EV1 walks in Unreal; ROS only sees its pose. Speed and grade come from a short
pose window, metabolic power from the §7.2 Pandolf/Tobler model, and
consumption from the same conversions the return field uses. Consumables are
integrated over **mission (PET) seconds**, never over Gazebo /clock or wall
time (proje.md §4.3). Every model value is a SCENARIO assumption.

By default, speeds above the walk-run transition are capped there: the walking
model is not validated for running. An explicit SCENARIO speed cap can meter
faster interactive motion without silently treating it as walking. Consumption
then extrapolates the existing walking formula; it is not running physiology.
The return planner and its walking speeds are unchanged.
A pose jump longer than `max_step_m` (teleport or seek) resets the window
instead of being read as motion.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from .cost_human import CrewMember, SuitModel, WalkModel, metabolic_power
from .redline import Rates, Resources


@dataclass(frozen=True)
class Motion:
    speed_m_s: float
    grade_percent: float
    capped: bool


class MotionWindow:
    def __init__(self, window_s: float = 2.0, max_step_m: float = 20.0,
                 *, scenario_speed_cap_m_s: float | None = None):
        if not (window_s > 0 and max_step_m > 0):
            raise ValueError("window_s and max_step_m must be positive")
        self.window_s = window_s
        self.max_step_m = max_step_m
        if scenario_speed_cap_m_s is not None and not (
                math.isfinite(scenario_speed_cap_m_s) and 0 < scenario_speed_cap_m_s <= 5.0):
            raise ValueError("SCENARIO speed cap must be finite and in (0, 5] m/s")
        self.scenario_speed_cap_m_s = scenario_speed_cap_m_s
        self._samples: deque[tuple[float, float, float, float]] = deque()
        self.resets = 0

    def add(self, t_s: float, x: float, y: float, z: float) -> None:
        if not all(math.isfinite(v) for v in (t_s, x, y, z)):
            raise ValueError("pose samples must be finite")
        if self._samples:
            last = self._samples[-1]
            if t_s <= last[0]:
                return  # out-of-order or duplicate sample
            if math.hypot(x - last[1], y - last[2]) > self.max_step_m:
                self._samples.clear()
                self.resets += 1
        self._samples.append((t_s, x, y, z))
        while len(self._samples) > 2 and t_s - self._samples[1][0] >= self.window_s:
            self._samples.popleft()

    @property
    def position(self) -> tuple[float, float, float] | None:
        return self._samples[-1][1:] if self._samples else None

    def motion(self, model: WalkModel) -> Motion:
        if len(self._samples) < 2:
            return Motion(0.0, 0.0, False)
        t0, x0, y0, z0 = self._samples[0]
        t1, x1, y1, z1 = self._samples[-1]
        run = math.hypot(x1 - x0, y1 - y0)
        speed = run / (t1 - t0)
        grade = 100.0 * (z1 - z0) / run if run > 0.05 else 0.0
        cap = (model.walk_run_speed_m_s if self.scenario_speed_cap_m_s is None
               else self.scenario_speed_cap_m_s)
        return Motion(min(speed, cap), grade, speed > cap)


def consumption(motion: Motion, eta: float, crew: CrewMember, suit: SuitModel,
                model: WalkModel) -> tuple[float, Rates]:
    """Metabolic power (W) and consumption rates for the current motion."""
    power = metabolic_power(motion.speed_m_s, motion.grade_percent, eta, crew, suit, model)
    return power, Rates.from_metabolic_power(power, suit)


def deplete(remaining: Resources, rates: Rates, dt_s: float) -> Resources:
    """Consume for `dt_s` mission seconds; a tank cannot go below empty."""
    if not (math.isfinite(dt_s) and dt_s >= 0):
        raise ValueError("dt_s must be finite and >= 0")
    return Resources(
        o2_kg=max(remaining.o2_kg - rates.o2_kg_s * dt_s, 0.0),
        co2_capacity_kg=max(remaining.co2_capacity_kg - rates.co2_kg_s * dt_s, 0.0),
        water_kg=max(remaining.water_kg - rates.water_kg_s * dt_s, 0.0),
        battery_wh=max(remaining.battery_wh - rates.battery_w * dt_s / 3600.0, 0.0),
    )
