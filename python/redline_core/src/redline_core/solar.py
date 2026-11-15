"""Mars time and daylight helpers (proje.md §4.3, §7.6; D014).

- LMST follows Mars24 (Allison & McEwen 2000) exactly as proje.md §4.3 writes it, with
  TAI−UTC = 37 s; it is therefore valid for UTC on or after 2017-01-01.
- Sun azimuth/elevation come from a SPICE table built by the data step (redline_data);
  this module only interpolates it and finds the next sunset, so ROS nodes need no SPICE.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np

SOL_S = 88775.244
_UNIX_JD = 2440587.5
_VALID_FROM = datetime(2017, 1, 1, tzinfo=timezone.utc)


def mars_sol_date(utc: datetime) -> float:
    if utc.tzinfo is None:
        raise ValueError("UTC must be timezone-aware")
    if utc < _VALID_FROM:
        raise ValueError("TAI−UTC = 37 s holds from 2017-01-01; earlier dates need the leap-second table")
    jd_utc = utc.timestamp() / 86400.0 + _UNIX_JD
    jd_tt = jd_utc + (37.0 + 32.184) / 86400.0
    return (jd_tt - 2405522.0028779) / 1.0274912517


def lmst_hours(utc: datetime, lon_east_deg: float) -> float:
    mtc = (24.0 * mars_sol_date(utc)) % 24.0
    return (mtc + lon_east_deg / 15.0) % 24.0


def format_hours(hours: float) -> str:
    total = int(round(hours * 3600.0)) % 86400
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def interpolate(table_t: np.ndarray, values: np.ndarray, t: float) -> float:
    """Linear interpolation inside the table; NaN outside it (no extrapolation)."""
    if not (table_t[0] <= t <= table_t[-1]):
        return math.nan
    return float(np.interp(t, table_t, values))


def next_sunset(table_t: np.ndarray, elevation_deg: np.ndarray, t: float) -> float:
    """Time of the next downward crossing of elevation 0 at or after t; NaN if none in the table."""
    start = int(np.searchsorted(table_t, t, side="right")) - 1
    for i in range(max(start, 0), len(table_t) - 1):
        a, b = elevation_deg[i], elevation_deg[i + 1]
        if a >= 0.0 > b:
            crossing = table_t[i] + (table_t[i + 1] - table_t[i]) * a / (a - b)
            if crossing >= t:
                return float(crossing)
    return math.nan


def daylight_budget_s(table_t: np.ndarray, elevation_deg: np.ndarray, t: float, dusk_s: float) -> float:
    """(t_sunset − T_dusk) − t: time left to stay out before the FR-12 dusk limit (§7.6).

    Before sunrise (sun below the horizon) there is no budget: −inf.
    """
    if interpolate(table_t, elevation_deg, t) < 0.0:
        return -math.inf
    sunset = next_sunset(table_t, elevation_deg, t)
    return sunset - dusk_s - t if math.isfinite(sunset) else math.nan
