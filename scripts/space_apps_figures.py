"""Slide figures for the Space Apps deck, drawn only from evidence files (docs/SPACE_APPS_SUNUM_PLANI.md).

  fig_rad_storm.png   ARCHIVE MSL RAD E dose rate, sol 4190 (steps, never interpolated; proje.md §6.3)
  fig_sensitivity.png docs/verification/SENSITIVITY.json (DERIVED terrain, SCENARIO parameters)
  fig_apxs.png        docs/verification/APXS_PRECISION.json (DERIVED from 690 ARCHIVE measurements)
Palette: validated two-slot categorical (dataviz reference palette, light surface). Run in the REDLINE venv.
Output: docs/figures/space_apps/
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/space_apps"
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"


def style(ax, title: str, subtitle: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=11)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=17, color=INK, fontweight="bold", pad=28)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=11, color=INK2)


def source(fig, text: str) -> None:
    fig.text(0.01, 0.01, text, fontsize=9, color=MUTED)


def rad_storm() -> None:
    rows = list(csv.DictReader((ROOT / "data/env/rad_4190.csv").open(encoding="utf-8")))
    t = [datetime.fromisoformat(r["utc"].replace("Z", "+00:00")) for r in rows]
    e = [float(r["dose_e_ugy_h"]) for r in rows]
    window = [(a, b) for a, b in zip(t, e) if 3 <= a.hour + a.minute / 60 <= 9]
    rad = json.loads((ROOT / "docs/verification/T6_RAD.json").read_text(encoding="utf-8"))
    light = json.loads((ROOT / "docs/verification/LIGHT_TIME_SOL4190.json").read_text(encoding="utf-8"))
    alarm = datetime.fromisoformat(rad["checks"][8]["observed_utc"])
    peak = datetime.fromisoformat(rad["checks"][7]["observed_utc"])
    peak_v, base_v = rad["checks"][7]["observed"], rad["checks"][0]["observed"]
    trip = light["events"]["alarm_utc"]["round_trip_min"]
    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=150)
    ax.plot([a for a, _ in window], [b for _, b in window], drawstyle="steps-post", color=BLUE, linewidth=2)
    for when, label, align in ((alarm, "first alarm 05:21:50  ", "right"),
                               (peak, f"  peak {peak_v:.0f} µGy/h 06:15:19", "left")):
        ax.axvline(when, color=AXIS, linewidth=1, linestyle="--")
        ax.text(when, peak_v * 1.04, label, fontsize=11, color=INK2, ha=align)
    earth = alarm + timedelta(minutes=trip)
    ax.annotate("", xy=(earth, 40), xytext=(alarm, 40),
                arrowprops={"arrowstyle": "<->", "color": ORANGE, "linewidth": 2})
    ax.text(alarm + (earth - alarm) / 2, 52, f"ask Earth and hear back: {trip:.0f} min", color=INK, fontsize=12,
            ha="center")
    ax.set_ylim(0, peak_v * 1.15)
    ax.set_ylabel("dose rate, µGy/h (tissue-equivalent detector)", color=INK2, fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    style(ax, f"Radiation rose {peak_v / base_v:.0f}× in {(peak - alarm).total_seconds() / 60:.0f} minutes",
          "Curiosity at Gale crater, 20 May 2024 (UTC). Solar storm; decision time is shorter than Earth's reply.")
    source(fig, "Data: NASA PDS, MSL RAD RDR sol 4190 (ARCHIVE), shown as recorded steps. "
                "Light time: NAIF SPICE de440s (DERIVED). REDLINE.")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "fig_rad_storm.png", facecolor=SURFACE)
    plt.close(fig)


LABELS = {"sep_limit_min": "storm warning limit (15 / 30 min)",
          "speed_factor_unobserved": "speed over ground no robot has seen (0.6 / 0.85)",
          "tobler_peak_kmh": "walking speed (5 / 7 km/h)",
          "sigma_theta": "model-time uncertainty (10 / 30 %)",
          "slope_max_deg": "steepest allowed slope (20 / 30°)",
          "z_eps": "safety quantile (90 / 99 %)"}


def sensitivity() -> None:
    rep = json.loads((ROOT / "docs/verification/SENSITIVITY.json").read_text(encoding="utf-8"))
    base, bars = rep["base_km2"], rep["bars"][::-1]
    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=150)
    y = range(len(bars))
    for i, b in zip(y, bars):
        for value, color in ((b["metric_low"], BLUE), (b["metric_high"], ORANGE)):
            ax.barh(i + (0.19 if color == BLUE else -0.19), value - base, left=base, height=0.34, color=color,
                    edgecolor=SURFACE, linewidth=2)
    ax.axvline(base, color=INK2, linewidth=1.5)
    ax.text(base, -0.75, f" base {base:.2f} km²", color=INK2, fontsize=11, ha="left", va="center")
    ax.set_ylim(-0.95, len(bars) - 0.45)
    ax.set_yticks(list(y), [LABELS[b["parameter"]] for b in bars], fontsize=12)
    ax.set_xlabel("safe-return area during a storm warning, km²", color=INK2, fontsize=11)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    style(ax, "What moves the storm red line most",
          "Each assumption moved alone, low and high; all others at their values. Real BXW terrain, 4 m grid.")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", colors=INK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)]
    ax.legend(handles, ["low value", "high value"], frameon=False, loc="lower right", fontsize=11, labelcolor=INK2)
    source(fig, "DERIVED terrain (HiRISE-based Gale DEM), SCENARIO parameters. Local sensitivity, not validation. "
                "docs/verification/SENSITIVITY.json")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "fig_sensitivity.png", facecolor=SURFACE)
    plt.close(fig)


def apxs() -> None:
    rep = json.loads((ROOT / "docs/verification/APXS_PRECISION.json").read_text(encoding="utf-8"))
    oxides = ["SiO2", "FeO", "Al2O3", "MgO", "CaO", "Na2O"]
    names = {"SiO2": "SiO₂", "FeO": "FeO", "Al2O3": "Al₂O₃", "MgO": "MgO", "CaO": "CaO", "Na2O": "Na₂O"}
    measured = [100 * (1 - rep["oxides"][o]["sigma_1h_over_10min"]) for o in oxides]
    law = 100 * (1 - (1 / 6) ** 0.5)
    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=150)
    x = range(len(oxides))
    ax.bar([i - 0.2 for i in x], measured, width=0.38, color=BLUE, edgecolor=SURFACE, linewidth=2)
    ax.bar([i + 0.2 for i in x], [law] * len(oxides), width=0.38, color=ORANGE, edgecolor=SURFACE, linewidth=2)
    for i, m in zip(x, measured):
        ax.text(i - 0.2, m + 1.2, f"{m:.0f}%", ha="center", color=INK, fontsize=11)
    ax.text(len(oxides) - 0.8, law + 1.2, f"{law:.0f}%", ha="center", color=INK, fontsize=11)
    ax.set_xticks(list(x), [names[o] for o in oxides], fontsize=12)
    ax.set_ylim(0, 70)
    ax.set_ylabel("error reduction, measuring 1 h instead of 10 min", color=INK2, fontsize=11)
    handles = [plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)]
    ax.legend(handles, ["fit to 690 Curiosity measurements", "textbook counting law (√t)"], frameon=False,
              loc="upper left", fontsize=11, labelcolor=INK2)
    style(ax, "Measuring longer barely helps; placing the instrument well does",
          "Curiosity X-ray spectrometer (APXS) precision errors. Each cm of stand-off adds 6–24 % error.")
    ax.tick_params(axis="x", colors=INK)
    source(fig, "Data: NASA PDS Geosciences, MSL APXS supplement (Berger et al. 2020), ARCHIVE; fit DERIVED. "
                "docs/verification/APXS_PRECISION.json")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "fig_apxs.png", facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rad_storm()
    sensitivity()
    apxs()
    print(sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
