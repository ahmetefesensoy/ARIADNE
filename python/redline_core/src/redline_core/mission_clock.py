"""Mission (PET) clock arithmetic for `sim_clock` (proje.md §4.3).

PET = start + scale·(monotonic − monotonic_at_start), advanced only while
running. Pausing freezes PET; changing the scale re-anchors so PET stays
continuous. This clock never reads or drives Gazebo /clock. Seeking belongs to
the T6 scenario player and is not part of this minimal runner.
"""
from __future__ import annotations

import math


class MissionClockRunner:
    def __init__(self, start_s: float, scale: float, now_monotonic_s: float, running: bool = True):
        if not (math.isfinite(start_s) and start_s >= 0):
            raise ValueError("start PET must be finite and >= 0")
        self._check_scale(scale)
        self._anchor_pet = float(start_s)
        self._anchor_mono = float(now_monotonic_s)
        self._scale = float(scale)
        self._running = running

    @staticmethod
    def _check_scale(scale: float) -> None:
        if not (math.isfinite(scale) and scale > 0):
            raise ValueError("time scale must be finite and > 0")

    @property
    def scale(self) -> float:
        return self._scale

    @property
    def running(self) -> bool:
        return self._running

    def pet(self, now_monotonic_s: float) -> float:
        if not self._running:
            return self._anchor_pet
        return self._anchor_pet + self._scale * max(now_monotonic_s - self._anchor_mono, 0.0)

    def _reanchor(self, now_monotonic_s: float) -> None:
        self._anchor_pet = self.pet(now_monotonic_s)
        self._anchor_mono = now_monotonic_s

    def set_scale(self, scale: float, now_monotonic_s: float) -> None:
        self._check_scale(scale)
        self._reanchor(now_monotonic_s)
        self._scale = float(scale)

    def pause(self, now_monotonic_s: float) -> None:
        if self._running:  # idempotent
            self._reanchor(now_monotonic_s)
            self._running = False

    def resume(self, now_monotonic_s: float) -> None:
        if not self._running:  # idempotent: resuming a running clock must not move PET back
            self._anchor_mono = now_monotonic_s
            self._running = True


def split_seconds(pet_s: float) -> tuple[int, int]:
    """builtin_interfaces/Time fields for a PET value."""
    if not (math.isfinite(pet_s) and pet_s >= 0):
        raise ValueError("PET must be finite and >= 0")
    sec = math.floor(pet_s)
    nanosec = min(int(round((pet_s - sec) * 1e9)), 999_999_999)
    return int(sec), nanosec
