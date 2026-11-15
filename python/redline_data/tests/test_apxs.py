"""APXS supplement reader and precision fit on synthetic rows with known coefficients."""
import csv
import math

import numpy as np
import pytest

from redline_data.apxs import OXIDES, fit_precision, lifetime_s, read_supplement

COEF = {"exp_t": -0.12, "exp_v": 0.7, "per_cm_standoff": 0.2}


def write_rows(path, failed_row=True, exp_t=COEF["exp_t"]):
    rng = np.random.default_rng(7)
    n = 40
    t = rng.uniform(600, 30000, n)
    standoff = rng.uniform(-0.4, 3.0, n)
    values = {ox: rng.uniform(1.0, 50.0, n) for ox in OXIDES}
    header = ["Sol", "Target", "Preparation_method", "Standoff_distance", "Lifetime", "FWHM"]
    for ox in OXIDES:
        header += [ox, ox + "_error"]
    with path.open("w", encoding="cp1252", newline="") as handle:
        out = csv.writer(handle)
        out.writerow(header)
        for i in range(n):
            secs = int(t[i])
            row = [str(i), f"T{i}", "Sieve150µm-1mm" if i == 0 else "RU", f"{standoff[i]:.3f}",
                   f"{secs // 3600:02d}:{secs % 3600 // 60:02d}:{secs % 60:02d}", "150"]
            for ox in OXIDES:
                v = values[ox]
                sigma = 0.3 * (int(t[i]) / 3600.0) ** exp_t * (v[i] / np.median(v)) ** COEF["exp_v"] * \
                    math.exp(COEF["per_cm_standoff"] * max(standoff[i], 0.0))
                row += [f"{v[i]:.6f}", f"{sigma:.8f}"]
            out.writerow(row)
        if failed_row:  # a failed placement with absurd errors must not enter the fit
            out.writerow(["99", "Bad", "Failed", "0.1", "01:00:00", "150"] + ["10", "50"] * len(OXIDES))


def test_lifetime_is_parsed_from_hh_mm_ss():
    assert lifetime_s("03:13:53") == 3 * 3600 + 13 * 60 + 53
    with pytest.raises(ValueError):
        lifetime_s("3h")


def test_reader_decodes_cp1252_and_drops_failed_placements(tmp_path):
    path = tmp_path / "ds01.csv"
    write_rows(path)
    rows = read_supplement(path)
    assert len(rows) == 40 and all(r["Preparation_method"] != "Failed" for r in rows)
    assert rows[0]["Preparation_method"] == "Sieve150µm-1mm"


def test_fit_recovers_the_generating_coefficients(tmp_path):
    path = tmp_path / "ds01.csv"
    write_rows(path)
    fit = fit_precision(read_supplement(path), source={"url": "u", "sha256": "s", "doi": "d"})
    assert fit["provenance_status"] == "DERIVED" and fit["t_ref_s"] == 3600.0
    for ox in OXIDES:
        o = fit["oxides"][ox]
        assert o["n"] == 40
        assert o["exp_t"] == pytest.approx(COEF["exp_t"], abs=1e-4)
        assert o["exp_v"] == pytest.approx(COEF["exp_v"], abs=1e-4)
        assert o["per_cm_standoff"] == pytest.approx(COEF["per_cm_standoff"], abs=1e-4)
        assert o["sigma_ref_wt"] == pytest.approx(0.3, rel=1e-3)
        assert o["mad_log"] < 1e-4
    lo, hi = fit["calibrated_integration_s"]
    assert 600 <= lo < hi <= 30000


def test_fit_reports_how_badly_a_pure_sqrt_t_law_would_describe_the_errors(tmp_path):
    shallow, poisson = tmp_path / "shallow.csv", tmp_path / "poisson.csv"
    write_rows(shallow)
    write_rows(poisson, exp_t=-0.5)
    src = {"url": "u", "sha256": "s", "doi": "d"}
    worse = fit_precision(read_supplement(shallow), source=src)["oxides"]["SiO2"]["sqrt_law_mad_log"]
    exact = fit_precision(read_supplement(poisson), source=src)["oxides"]["SiO2"]["sqrt_law_mad_log"]
    assert worse > 0.1 > exact
