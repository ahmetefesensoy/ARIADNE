"""Mars time and daylight budget (proje.md §4.3, §7.6; D014)."""
import math
from datetime import datetime, timezone

import numpy as np
import pytest

from redline_core.solar import daylight_budget_s, format_hours, lmst_hours, mars_sol_date, next_sunset


def test_lmst_matches_rad_mars_time_stamps_within_a_minute():
    # ARCHIVE reference: RAD RDR sol 4190 headers (START_OBS_UTC -> START_OBS_MARS, MSL LMST at the
    # landing site 137.4417°E). The formula agrees to ~40 s (MSL derives its LMST from SCLK).
    utc = datetime(2024, 5, 19, 18, 30, 0, tzinfo=timezone.utc)
    rad = 8 * 60 + 26  # "4190 0:08:26"
    ours = lmst_hours(utc, 137.4417) * 3600.0
    assert abs(((ours - rad + 43200) % 86400) - 43200) < 60.0
    assert format_hours(lmst_hours(utc, 137.4417)) == "00:08:42"
    assert mars_sol_date(utc) - 49268 == pytest.approx(4190.6, abs=0.1)  # MSL sol = MSD − 49268


def test_lmst_rejects_naive_and_pre_2017_times():
    with pytest.raises(ValueError):
        lmst_hours(datetime(2024, 1, 1), 0.0)
    with pytest.raises(ValueError):
        lmst_hours(datetime(2012, 8, 6, tzinfo=timezone.utc), 137.4)


def table():
    t = np.arange(0.0, 3 * 86400.0, 600.0)
    el = 60.0 * np.sin(2 * np.pi * (t - 6 * 3600.0) / 86400.0)  # sunrise 06:00, sunset 18:00
    return t, el


def test_next_sunset_and_daylight_budget():
    t, el = table()
    assert next_sunset(t, el, 8 * 3600.0) == pytest.approx(18 * 3600.0, abs=1.0)
    budget = daylight_budget_s(t, el, 8 * 3600.0, 1800.0)
    assert budget == pytest.approx(10 * 3600.0 - 1800.0, abs=1.0)
    assert daylight_budget_s(t, el, 3 * 3600.0, 1800.0) == -math.inf  # before sunrise
    assert math.isnan(daylight_budget_s(t, el, 4 * 86400.0, 1800.0))  # outside the table
