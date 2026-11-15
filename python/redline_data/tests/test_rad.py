"""RAD RDR parser on a format excerpt (proje.md §6.3). Real-file values: scripts/verify_rad.py."""
from datetime import datetime, timezone

import pytest

from redline_data.rad import parse_doy_utc, parse_rad_text, read_rad_table, write_rad_table

EXCERPT = """[FILE]
SOFTWARE_VERSION=1.0
START_SOL=4190
START_TIME="2024-140 18:30:00"

[OBSERVATION: 00]
START_OBS_MARS="4190 0:08:26"
START_OBS_UTC="2024-140 18:30:00"

[DOSIMETRY_TOTAL_DOSE_B: 00]

6.66601

[DOSIMETRY_TOTAL_DOSE_E: 00]

5.56104

[DOSIMETRY_LET_B_A1: 00]
NUM_ROWS=1
1.0

[OBSERVATION: 01]
START_OBS_MARS="4190 0:08:27"
START_OBS_UTC="2024-140 18:30:01"

[OBSERVATION: 02]
START_OBS_MARS="4190 0:25:05"
START_OBS_UTC="2024-140 18:47:06"

[DOSIMETRY_TOTAL_DOSE_E: 02]

5.7

[DOSIMETRY_TOTAL_DOSE_B: 02]

6.9
"""


def test_day_of_year_utc():
    assert parse_doy_utc("2024-141 06:15:19") == datetime(2024, 5, 20, 6, 15, 19, tzinfo=timezone.utc)
    assert parse_doy_utc("2024-001 00:00:00") == datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_doses_are_matched_by_index_not_order():
    header, readings = parse_rad_text(EXCERPT.splitlines())
    assert header["START_SOL"] == "4190"
    assert [r.observation for r in readings] == [0, 2]  # observation 01 has no dose block
    first, second = readings
    assert (first.dose_b_ugy_h, first.dose_e_ugy_h) == (6.66601, 5.56104)
    assert (second.dose_b_ugy_h, second.dose_e_ugy_h) == (6.9, 5.7)  # E block came first in the file
    assert second.sol == 4190 and second.utc.hour == 18 and second.utc.minute == 47


def test_rejects_orphan_and_duplicate_blocks():
    with pytest.raises(ValueError, match="without an observation"):
        parse_rad_text((EXCERPT + "\n[DOSIMETRY_TOTAL_DOSE_B: 09]\n\n1.0\n").splitlines())
    with pytest.raises(ValueError, match="duplicate"):
        parse_rad_text((EXCERPT + "\n[DOSIMETRY_TOTAL_DOSE_B: 02]\n\n1.0\n").splitlines())


def test_table_round_trip_is_hash_checked(tmp_path):
    rdr = tmp_path / "RAD.TXT"
    rdr.write_text(EXCERPT, encoding="ascii")
    record = write_rad_table(rdr, tmp_path / "rad.csv", source_url="https://example.invalid/RAD.TXT")
    assert record["status"] == "ARCHIVE" and record["readings"] == 2
    readings = read_rad_table(tmp_path / "rad.csv")
    assert readings[1].dose_e_ugy_h == 5.7 and readings[0].utc.isoformat() == "2024-05-19T18:30:00+00:00"
    with pytest.raises(FileExistsError):
        write_rad_table(rdr, tmp_path / "rad.csv")
    (tmp_path / "rad.csv").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        read_rad_table(tmp_path / "rad.csv")
