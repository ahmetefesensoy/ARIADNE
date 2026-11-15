"""SCENARIO orientation walkthrough. This creates no science measurements/products.

ROS owns progress; Unreal only requests the next interaction. Existing mission
phase numbers are the frozen redline_msgs/MissionState contract.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class IntroLocations:
    briefing_xy: tuple[float, float]
    station_xy: tuple[float, float]
    radius_m: float = 4.0

    def __post_init__(self):
        if (not all(math.isfinite(v) for p in (self.briefing_xy, self.station_xy) for v in p)
                or not math.isfinite(self.radius_m) or not 0 < self.radius_m <= 10):
            raise ValueError("finite SCENARIO locations and a 0..10 m interaction radius required")


def advance_intro(phase: int, position_xy, age_s: float, locations: IntroLocations) -> tuple[int, str]:
    """Reject stale/remote interactions; keep SEP/RETURN authority outside the client."""
    if (position_xy is None or not math.isfinite(age_s) or not 0 <= age_s <= 2
            or not all(math.isfinite(v) for v in position_xy)):
        raise ValueError("fresh finite EV1 state required")
    if phase == 0:
        target, next_phase, event = locations.briefing_xy, 2, "GO_AFTER_BRIEFING"
    elif phase == 2:
        target, next_phase, event = locations.station_xy, 3, "FIELD_CONTEXT_OPENED"
    elif phase == 3:
        target, next_phase, event = locations.station_xy, 4, "CONTEXT_REVIEWED_RETURN_REQUESTED"
    elif phase == 4:
        target, next_phase, event = locations.briefing_xy, 6, "ORIENTATION_RETURN_COMPLETE"
    else:
        raise ValueError("no orientation interaction in this mission phase")
    if math.dist(position_xy, target) > locations.radius_m:
        raise ValueError("approach the current interaction point")
    return next_phase, event
