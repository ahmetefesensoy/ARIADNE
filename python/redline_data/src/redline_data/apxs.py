"""MSL APXS supplement reader and precision fit (proje.md §9.1 calibration rule, §9.2 B1).

Source: PDS Geosciences ``urn:nasa:pds:msl_apxs_supplement_sols_0_2301`` table ds01 (Berger et al.
2020, doi:10.1029/2020JE006536), cp1252 CSV, one row per APXS integration with oxide wt%,
"Precision Error" columns, Lifetime (HH:MM:SS) and Standoff (cm). Status ARCHIVE.

The fit is ordinary least squares on log error per oxide:
    log e = log σ_ref + exp_t·log(t/3600) + exp_v·log(v/v_ref) + per_cm_standoff·max(standoff, 0)
v_ref is the oxide's median abundance. Rows with Preparation_method "Failed" are dropped. The
output also gives the residual of the spec's counting law (exp_t fixed at -0.5, the other terms
refit), so it can be compared with the archive. The output is DERIVED.
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import numpy as np

from redline_core.apxs_precision import SCHEMA

OXIDES = ("Na2O", "MgO", "Al2O3", "SiO2", "P2O5", "SO3", "Cl", "K2O", "CaO", "TiO2", "Cr2O3", "MnO", "FeO")
T_REF_S = 3600.0
_HMS = re.compile(r"^\s*(\d+):(\d{2}):(\d{2})\s*$")


def lifetime_s(text: str) -> int:
    match = _HMS.match(text)
    if not match:
        raise ValueError(f"Lifetime must be HH:MM:SS, got {text!r}")
    h, m, s = (int(g) for g in match.groups())
    return h * 3600 + m * 60 + s


def read_supplement(path: Path | str) -> list[dict]:
    with Path(path).open(encoding="cp1252", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row["Preparation_method"].strip() != "Failed"]


def _number(text: str) -> float:
    try:
        return float(text)
    except (TypeError, ValueError):
        return math.nan


def fit_precision(rows: list[dict], source: dict) -> dict:
    t = np.array([lifetime_s(r["Lifetime"]) for r in rows], dtype=float)
    standoff = np.array([_number(r["Standoff_distance"]) for r in rows])
    gap = np.maximum(standoff, 0.0)
    oxides = {}
    used = np.zeros(len(rows), dtype=bool)
    for ox in OXIDES:
        v = np.array([_number(r[ox]) for r in rows])
        e = np.array([_number(r[ox + "_error"]) for r in rows])
        m = np.isfinite(v) & np.isfinite(e) & (v > 0) & (e > 0) & (t > 0) & np.isfinite(gap)
        used |= m
        v_ref = float(np.median(v[m]))
        design = np.column_stack([np.ones(m.sum()), np.log(t[m] / T_REF_S), np.log(v[m] / v_ref), gap[m]])
        coef, *_ = np.linalg.lstsq(design, np.log(e[m]), rcond=None)
        mad = float(np.median(np.abs(np.log(e[m]) - design @ coef)))
        # The counting law of proje.md §9.2 B1: exp_t fixed at -0.5, the other terms refit.
        counting = np.log(e[m]) + 0.5 * np.log(t[m] / T_REF_S)
        rest = design[:, [0, 2, 3]]
        sqrt_coef, *_ = np.linalg.lstsq(rest, counting, rcond=None)
        sqrt_mad = float(np.median(np.abs(counting - rest @ sqrt_coef)))
        oxides[ox] = {"v_ref_wt": v_ref, "sigma_ref_wt": float(math.exp(coef[0])), "exp_t": float(coef[1]),
                      "exp_v": float(coef[2]), "per_cm_standoff": float(coef[3]), "mad_log": mad,
                      "sqrt_law_mad_log": sqrt_mad, "n": int(m.sum())}
    return {"schema": SCHEMA, "provenance_status": "DERIVED", "source": dict(source), "t_ref_s": T_REF_S,
            "calibrated_integration_s": [float(t[used].min()), float(t[used].max())],
            "calibrated_standoff_cm": [0.0, float(gap[used].max())],
            "rows_used": int(used.sum()),
            "model": "log e = log sigma_ref + exp_t log(t/t_ref) + exp_v log(v/v_ref) + per_cm_standoff max(s,0)",
            "oxides": oxides}
