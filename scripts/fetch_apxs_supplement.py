"""Fetch the MSL APXS supplement and fit the APXS precision model (proje.md §9.1, §9.2 B1).

Downloads the PDS Geosciences table ds01 and its label into data/raw/instruments/apxs/ (each
file in that directory only; the SHA-256 of the CSV must match the pin recorded on 2026-11-14 in
research/notes/APXS_HEDEF_ON_KONTROL.json). Writes the DERIVED model to
data/derived/instruments/apxs_precision_v1.json and the comparison with the spec's counting law to
docs/verification/APXS_PRECISION.json. Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from redline_core.apxs_precision import ApxsPrecision
from redline_data.apxs import fit_precision, read_supplement
from redline_data.rad import sha256_file

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://pds-geosciences.wustl.edu/msl/urn-nasa-pds-msl_apxs_supplement_sols_0_2301/data/"
CSV, LABEL = "ds01_2020je006536rr.csv", "ds01_2020je006536rr.xml"
CSV_SHA256 = "6a6e4359a543b315783bc672b9a173e4930592ba62c071d5c93b9a7b85584f8c"
DOI = "10.1029/2020JE006536"


def fetch(url: str, path: Path) -> None:
    if path.exists():
        return
    request = urllib.request.Request(url, headers={"User-Agent": "redline-research-client"})
    tmp = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(request, timeout=300) as response, tmp.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    tmp.rename(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default="data/derived/instruments/apxs_precision_v1.json")
    parser.add_argument("--report", default="docs/verification/APXS_PRECISION.json")
    args = parser.parse_args()
    raw = ROOT / "data/raw/instruments/apxs"
    raw.mkdir(parents=True, exist_ok=True)
    for name in (CSV, LABEL):
        fetch(BASE + name, raw / name)
    observed = sha256_file(raw / CSV)
    if observed != CSV_SHA256:
        print(f"{CSV}: sha256 {observed} != pinned {CSV_SHA256}", file=sys.stderr)
        return 1
    rows = read_supplement(raw / CSV)
    source = {"url": BASE + CSV, "label_url": BASE + LABEL, "sha256": observed, "doi": DOI,
              "label_sha256": sha256_file(raw / LABEL), "status": "ARCHIVE",
              "citation": "Berger, J. A. et al. (2020), JGR Planets 125(12), doi:10.1029/2020JE006536",
              "columns": "oxide wt% and '<oxide>_error' = 'Precision Error' (label); Lifetime HH:MM:SS; "
                         "Standoff cm (negative = contact sensor pressed in)"}
    model = fit_precision(rows, source=source)
    model["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    model_path = ROOT / args.model
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps(model, indent=1) + "\n", encoding="utf-8")
    loaded = ApxsPrecision.load(model_path)  # the runtime loader accepts what was written

    table = {ox: {"exp_t": round(o["exp_t"], 3), "counting_law_exp_t": -0.5,
                  "per_cm_standoff": round(o["per_cm_standoff"], 3), "mad_log": round(o["mad_log"], 3),
                  "counting_law_mad_log": round(o["sqrt_law_mad_log"], 3),
                  "sigma_ref_wt": round(o["sigma_ref_wt"], 4), "v_ref_wt": round(o["v_ref_wt"], 3),
                  "sigma_1h_over_10min": round(loaded.sigma_wt(ox, o["v_ref_wt"], 3600.0)
                                               / loaded.sigma_wt(ox, o["v_ref_wt"], 600.0), 3),
                  "n": o["n"]}
             for ox, o in model["oxides"].items()}
    better = sorted(ox for ox, r in table.items() if r["mad_log"] < r["counting_law_mad_log"])
    report = {"check": "APXS precision error versus integration time (proje.md §9.2 B1 counting law)",
              "status": "DERIVED from ARCHIVE", "source": source, "rows_used": model["rows_used"],
              "rows_excluded": "Preparation_method == Failed",
              "calibrated_integration_s": model["calibrated_integration_s"],
              "calibrated_standoff_cm": model["calibrated_standoff_cm"],
              "model": model["model"], "oxides": table,
              "fitted_model_fits_better_than_counting_law": better,
              "conclusion": ("The archive's precision errors shrink far more slowly with integration than "
                             "sqrt(t) for the major oxides and grow with standoff; simulated APXS products "
                             "use the fitted DERIVED model, not the counting law."),
              "model_file": args.model, "generated_utc": model["generated_utc"]}
    report_path = ROOT / args.report
    report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({ox: (r["exp_t"], r["per_cm_standoff"], r["sigma_1h_over_10min"]) for ox, r in table.items()}))
    print(f"better than counting law: {better}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
