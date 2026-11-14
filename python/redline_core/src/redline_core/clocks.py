"""Typed physics and mission times; historical replay only follows PET.

No Mars24 conversion is claimed here. The UTC replay epoch/rate comes from
an explicit scenario; it is never inferred from a simulator /clock value.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class PhysicsTime:
    """Gazebo simulation seconds since its own epoch, not PET."""

    seconds: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("Physics seconds must be finite and nonnegative")


@dataclass(frozen=True)
class MissionTime:
    """Elapsed mission/PET seconds; seeking does not advance physics."""

    seconds: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("Mission seconds must be finite and nonnegative")


@dataclass(frozen=True)
class ReplayMapping:
    """utc = utc0 + rate * (mission - mission0), proje.md §4.3.

    rate maps PET to historical data time; playback/wall-clock acceleration
    is a different responsibility. This mapping never mutates a clock.
    """

    utc0: datetime
    mission0: MissionTime
    rate: float = 1.0

    def __post_init__(self) -> None:
        if self.utc0.tzinfo is None or self.utc0.utcoffset() is None:
            raise ValueError("Historical epoch must include a UTC offset")
        if type(self.mission0) is not MissionTime:
            raise TypeError("Replay mapping requires a mission/PET epoch")
        if not math.isfinite(self.rate) or self.rate <= 0:
            raise ValueError("Historical replay rate must be finite and positive")

    def historical_utc(self, mission: MissionTime) -> datetime:
        """Map a PET observation to timezone-aware historical UTC."""
        if type(mission) is not MissionTime:
            raise TypeError("Use mission/PET time, not physics or wall time")
        delta = self.rate * (mission.seconds - self.mission0.seconds)
        if not math.isfinite(delta):
            raise ValueError("Replay time is outside the representable UTC range")
        try:
            return self.utc0.astimezone(timezone.utc) + timedelta(seconds=delta)
        except OverflowError as error:
            raise ValueError("Replay time is outside the representable UTC range") from error
