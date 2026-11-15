"""MSL RAD RDR dose-rate parser (proje.md §6.3; D012).

RDR text files are a sequence of ``[SECTION: NN]`` blocks. ``[OBSERVATION: NN]`` holds
``START_OBS_UTC="YYYY-DOY hh:mm:ss"`` and ``START_OBS_MARS="SOL h:mm:ss"``; the first
non-empty line after ``[DOSIMETRY_TOTAL_DOSE_B: NN]`` / ``[..._E: NN]`` is one number.
Doses are matched to observations **by NN**, never by order: dose blocks exist only for
some observations (even NN in the 2024 files). Values are kept as recorded (µGy/h per
Hassler et al. 2014; the SIS writes the unit inconsistently) and are never interpolated.
Status ARCHIVE: these are NASA measurements, not model output.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SECTION = re.compile(r"^\[([A-Z0-9_]+):\s*(\d+)\]\s*$")
_FILE_SECTION = re.compile(r"^\[FILE\]\s*$")
_KEY = re.compile(r'^([A-Z_]+)="?([^"]*)"?\s*$')


@dataclass(frozen=True)
class RadReading:
    sol: int
    observation: int
    utc: datetime
    mars_time: str
    dose_b_ugy_h: float | None
    dose_e_ugy_h: float | None


def parse_doy_utc(text: str) -> datetime:
    """'2024-141 06:15:19' (year, day of year) -> aware UTC datetime."""
    date, clock = text.strip().split()
    year, doy = date.split("-")
    hh, mm, ss = (int(v) for v in clock.split(":"))
    return datetime(int(year), 1, 1, hh, mm, ss, tzinfo=timezone.utc) + timedelta(days=int(doy) - 1)


def parse_rad_text(lines) -> tuple[dict, list[RadReading]]:
    """Header fields of [FILE] and one reading per observation that has a dose value."""
    header: dict[str, str] = {}
    obs: dict[int, dict] = {}
    dose: dict[tuple[str, int], float] = {}
    section, index, waiting = None, None, None
    for raw in lines:
        line = raw.strip()
        if _FILE_SECTION.match(line):
            section, index, waiting = "FILE", None, None
            continue
        match = _SECTION.match(line)
        if match:
            section, index = match.group(1), int(match.group(2))
            waiting = section if section in ("DOSIMETRY_TOTAL_DOSE_B", "DOSIMETRY_TOTAL_DOSE_E") else None
            if section == "OBSERVATION":
                if index in obs:
                    raise ValueError(f"duplicate OBSERVATION {index}")
                obs[index] = {}
            continue
        if not line:
            continue
        if waiting is not None:
            key = (waiting[-1], index)
            if key in dose:
                raise ValueError(f"duplicate {waiting} {index}")
            dose[key] = float(line)
            waiting = None
            continue
        kv = _KEY.match(line)
        if kv and section == "FILE":
            header[kv.group(1)] = kv.group(2)
        elif kv and section == "OBSERVATION":
            obs[index][kv.group(1)] = kv.group(2)
    orphans = sorted({i for (_, i) in dose} - set(obs))
    if orphans:
        raise ValueError(f"dose blocks without an observation: {orphans[:5]}")
    readings = []
    for i in sorted(obs):
        b, e = dose.get(("B", i)), dose.get(("E", i))
        if b is None and e is None:
            continue
        fields = obs[i]
        if "START_OBS_UTC" not in fields:
            raise ValueError(f"OBSERVATION {i} has no START_OBS_UTC")
        mars = fields.get("START_OBS_MARS", "")
        sol = int(mars.split()[0]) if mars else int(header.get("START_SOL", -1))
        readings.append(RadReading(sol, i, parse_doy_utc(fields["START_OBS_UTC"]), mars, b, e))
    return header, readings


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_rad_table(rdr: Path, out_csv: Path, *, label: Path | None = None, source_url: str = "") -> dict:
    """Parse one RDR file into an immutable CSV + JSON sidecar (ARCHIVE)."""
    out_csv, sidecar = Path(out_csv), Path(out_csv).with_suffix(".json")
    for path in (out_csv, sidecar):
        if path.exists():
            raise FileExistsError(f"{path} exists; environment tables are immutable")
    with Path(rdr).open(encoding="ascii", errors="strict") as handle:
        header, readings = parse_rad_text(handle)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sol", "observation", "utc", "mars_time", "dose_b_ugy_h", "dose_e_ugy_h"])
        for r in readings:
            writer.writerow([r.sol, r.observation, r.utc.strftime("%Y-%m-%dT%H:%M:%SZ"), r.mars_time,
                             "" if r.dose_b_ugy_h is None else repr(r.dose_b_ugy_h),
                             "" if r.dose_e_ugy_h is None else repr(r.dose_e_ugy_h)])
    record = {
        "schema": "redline.rad_table.v1", "status": "ARCHIVE",
        "product": Path(rdr).name, "source_url": source_url,
        "rdr_sha256": sha256_file(rdr), "label_sha256": sha256_file(label) if label else None,
        "csv_sha256": sha256_file(out_csv), "file_header": header,
        "readings": len(readings), "unit": "uGy/h (as recorded; Hassler et al. 2014)",
        "rule": "doses matched to observations by NN; stepwise, never interpolated (proje.md §6.3)",
    }
    with sidecar.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(record, indent=1) + "\n")
    return record


def read_rad_table(path: Path) -> list[RadReading]:
    """Read a table written by :func:`write_rad_table` after checking its recorded hash."""
    path = Path(path)
    sidecar = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if sha256_file(path) != sidecar["csv_sha256"]:
        raise ValueError(f"{path}: SHA-256 does not match its sidecar")
    out = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out.append(RadReading(int(row["sol"]), int(row["observation"]),
                                  datetime.strptime(row["utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc),
                                  row["mars_time"],
                                  float(row["dose_b_ugy_h"]) if row["dose_b_ugy_h"] else None,
                                  float(row["dose_e_ugy_h"]) if row["dose_e_ugy_h"] else None))
    return out
