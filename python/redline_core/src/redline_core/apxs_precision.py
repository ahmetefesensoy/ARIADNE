"""APXS precision model for simulated contact science (proje.md §9.1, §9.2 B1).

The spec's σ_i(t) = σ_ref,i·sqrt(t_ref/t) assumes pure counting statistics. The MSL APXS
supplement (Berger et al. 2020, doi:10.1029/2020JE006536; ARCHIVE) reports "precision error"
that shrinks far more slowly for the major oxides, and that grows with sensor standoff. The
model here is the DERIVED fit of those columns (``redline_data.apxs.fit_precision``):

    log σ = log σ_ref + exp_t·log(t/t_ref) + exp_v·log(v/v_ref) + per_cm_standoff·max(standoff, 0)

with σ and v in wt%, t the integration (s) and standoff in cm (negative = contact sensor pressed
in, treated as touching). No extrapolation: integration and standoff outside the fitted range are
refused. A simulated product that uses this model is SIMULATED; the model itself is DERIVED.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "redline.apxs_precision.v1"


@dataclass(frozen=True)
class OxidePrecision:
    v_ref_wt: float
    sigma_ref_wt: float
    exp_t: float
    exp_v: float
    per_cm_standoff: float
    mad_log: float
    n: int


@dataclass(frozen=True)
class ApxsPrecision:
    t_ref_s: float
    integration_s: tuple[float, float]
    standoff_cm: tuple[float, float]
    oxides: dict[str, OxidePrecision]
    source: dict

    @classmethod
    def load(cls, path: Path | str) -> "ApxsPrecision":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA:
            raise ValueError(f"{path}: schema must be {SCHEMA}")
        if data.get("provenance_status") != "DERIVED":
            raise ValueError(f"{path}: an APXS precision fit is DERIVED from ARCHIVE data")
        oxides = {name: OxidePrecision(float(o["v_ref_wt"]), float(o["sigma_ref_wt"]), float(o["exp_t"]),
                                       float(o["exp_v"]), float(o["per_cm_standoff"]), float(o["mad_log"]),
                                       int(o["n"]))
                  for name, o in data["oxides"].items()}
        lo_t, hi_t = (float(v) for v in data["calibrated_integration_s"])
        lo_s, hi_s = (float(v) for v in data["calibrated_standoff_cm"])
        return cls(float(data["t_ref_s"]), (lo_t, hi_t), (lo_s, hi_s), oxides, dict(data["source"]))

    def sigma_wt(self, oxide: str, value_wt: float, integration_s: float, standoff_cm: float = 0.0) -> float:
        """1σ precision error (wt%) of one oxide for one simulated APXS integration."""
        o = self.oxides[oxide]
        if not value_wt > 0.0:
            raise ValueError("abundance must be positive wt%")
        if not self.integration_s[0] <= integration_s <= self.integration_s[1]:
            raise ValueError(f"integration {integration_s:.0f} s outside the calibrated range "
                             f"{self.integration_s[0]:.0f}-{self.integration_s[1]:.0f} s")
        gap = max(float(standoff_cm), 0.0)
        if gap > self.standoff_cm[1]:
            raise ValueError(f"standoff {gap:.2f} cm outside the calibrated range (<= {self.standoff_cm[1]:.2f} cm)")
        return o.sigma_ref_wt * math.exp(o.exp_t * math.log(integration_s / self.t_ref_s)
                                         + o.exp_v * math.log(value_wt / o.v_ref_wt) + o.per_cm_standoff * gap)

    def provenance(self) -> dict:
        return {"status": "DERIVED", "source_url": self.source.get("url", ""),
                "source_sha256": self.source.get("sha256", ""), "doi": self.source.get("doi", ""),
                "model": SCHEMA}
