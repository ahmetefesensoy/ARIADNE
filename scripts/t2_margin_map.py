"""T2 acceptance artifact: the first BXW margin map (proje.md §18, T2).

Reads only the T1-accepted products (SHA256 checked against the accepted run
manifest), builds the 4 m planning layers, computes the EV1 return field, margin
and red/yellow lines with redline_core, and writes a PNG + JSON summary under
data/derived/BXW/t2-run-<UTC>/. Terrain is DERIVED; crew, suit, resources and
habitat position are SCENARIO, so the map is a SCENARIO product, not a plan.
Run inside the REDLINE venv with the data and core requirements installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

from redline_core.cost_human import UNOBSERVED, metabolic_power, prepare_terrain, walking_speed
from redline_core.grid import Grid, block_detrended_relief, block_reduce, north_up_to_grid
from redline_core.params import load_crew, load_models
from redline_core.redline import (
    LIM_BATTERY,
    LIM_CO2,
    LIM_NONE,
    LIM_O2,
    LIM_SHELTER,
    LIM_WATER,
    Rates,
    Resources,
    margin_for_crew,
    region_contours,
)
from redline_core.walkback import walkable_components, walkback

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "data/stac/BXW/t1-run-lfDo4ErT/run_manifest.json"
INPUTS = {
    "dem_plan_4m": "data/derived/BXW/dem_plan_4m.tif",
    "dem_enu": "data/derived/BXW/dem_enu.tif",
    "slope_5m": "data/derived/BXW/terrain/slope_5m.tif",
    "slope_2m": "data/derived/BXW/terrain/slope_2m.tif",
    "slope_sigma": "data/derived/BXW/comparison/slope_sigma.tif",
}
EXPECTED_TRANSFORM = {4.0: (4.0, 0.0, -1500.0, 0.0, -4.0, 1500.0), 1.0: (1.0, 0.0, -1500.0, 0.0, -1.0, 1500.0)}
LIM_NAMES = {LIM_O2: "O2", LIM_CO2: "CO2", LIM_WATER: "WATER", LIM_BATTERY: "BATTERY", LIM_SHELTER: "SHELTER",
             LIM_NONE: "NONE"}

# Light-mode chart tokens (dataviz reference palette).
SURFACE, INK, INK_2, MUTED, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#d8d7d0"
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING_MID = "#f0efec"
RED_ARM = ["#e34948", "#f08b8a", "#f6c4c3"]  # strong -> light, toward the gray midpoint
CRITICAL, WARNING = "#d03b3b", "#fab219"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_grid_order(path: Path, resolution: float) -> np.ndarray:
    with rasterio.open(path) as src:
        transform = tuple(round(v, 9) for v in tuple(src.transform)[:6])
        if transform != EXPECTED_TRANSFORM[resolution]:
            raise SystemExit(f"{path}: transform {transform} is not the accepted {resolution} m local grid")
        data = src.read(1, masked=True).astype(float).filled(np.nan)
    return north_up_to_grid(data)


def nearest_in_largest_component(labels: np.ndarray, cell: tuple[int, int]) -> tuple[tuple[int, int], dict]:
    """SCENARIO habitat: the cell nearest to the request inside the largest walkable region."""
    sizes = np.bincount(labels[labels >= 0])
    if sizes.size == 0:
        raise SystemExit("no walkable cell in the planning grid")
    largest = int(np.argmax(sizes))
    members = np.argwhere(labels == largest)
    best = members[np.argmin(np.hypot(members[:, 0] - cell[0], members[:, 1] - cell[1]))]
    requested_label = int(labels[cell])
    info = {
        "components": int(sizes.size),
        "largest_cells": int(sizes[largest]),
        "largest_fraction_of_walkable": float(sizes[largest] / sizes.sum()),
        "requested_cell_component_cells": int(sizes[requested_label]) if requested_label >= 0 else 0,
    }
    return (int(best[0]), int(best[1])), info


MIN_DRAWN_HOLE_M2 = 1.0e4  # figure only: holes smaller than 0.01 km² are not outlined


def signed_area_m2(ring: np.ndarray) -> float:
    x, y = ring[:, 0], ring[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def summary_stats(values: np.ndarray) -> dict:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"count": 0}
    q = np.percentile(finite, [5, 50, 95])
    return {"count": int(finite.size), "min": float(finite.min()), "p05": float(q[0]), "p50": float(q[1]),
            "p95": float(q[2]), "max": float(finite.max())}


def plot(path: Path, extent, w_eps_min, margin_min, banned_or_unreachable, habitat_xy, red, yellow, caption,
         title="BXW · ilk margin haritası (T2) — SCENARIO parametrelerle ön sonuç, plan değildir"):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.patheffects as pe
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, ListedColormap, TwoSlopeNorm
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": INK, "axes.labelcolor": INK_2,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": "#c3c2b7"})
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 6.6), dpi=150, facecolor=SURFACE, constrained_layout=True)
    km = [e / 1000.0 for e in extent]
    mask_cmap = ListedColormap([NEUTRAL])
    halo = [pe.Stroke(linewidth=3.4, foreground=INK), pe.Normal()]

    def base(ax, title):
        ax.set_facecolor(SURFACE)
        ax.set_title(title, loc="left", fontsize=11, color=INK)
        ax.set_xlabel("doğu x (km, BXW yerel ENU)")
        ax.set_ylabel("kuzey y (km)")
        ax.imshow(np.where(banned_or_unreachable, 1.0, np.nan), origin="lower", extent=km, cmap=mask_cmap,
                  interpolation="nearest")
        ax.plot(habitat_xy[0] / 1000, habitat_xy[1] / 1000, marker="s", ms=8, mfc=INK, mec=SURFACE, mew=1.5)
        ax.annotate("habitat", (habitat_xy[0] / 1000, habitat_xy[1] / 1000), xytext=(8, 8),
                    textcoords="offset points", color=INK, fontsize=9)

    sequential = LinearSegmentedColormap.from_list("blue_seq", BLUE)
    w_plot = np.where(np.isfinite(w_eps_min), w_eps_min, np.nan)  # unreachable = inf -> masked
    vmax = float(np.nanpercentile(w_plot, 99)) if np.isfinite(w_plot).any() else 1.0
    a = axes[0]
    image = a.imshow(w_plot, origin="lower", extent=km, cmap=sequential, vmin=0.0, vmax=vmax,
                     interpolation="nearest")
    base(a, "A · Risk düzeltmeli dönüş süresi W_ε (dk)")
    bar = fig.colorbar(image, ax=a, shrink=0.82, pad=0.02, extend="max")
    bar.set_label("dk (99. yüzdelikte kırpıldı)", color=INK_2)

    diverging = LinearSegmentedColormap.from_list("red_blue", [RED_ARM[0], RED_ARM[1], RED_ARM[2], DIVERGING_MID,
                                                                BLUE[1], BLUE[3], BLUE[5]])
    m_plot = np.where(np.isfinite(margin_min), margin_min, np.nan)
    negative, positive = m_plot[m_plot < 0], m_plot[m_plot > 0]
    low = -float(np.percentile(-negative, 99)) if negative.size else -1.0
    high = float(np.percentile(positive, 99)) if positive.size else 1.0
    b = axes[1]
    image = b.imshow(np.clip(m_plot, low, high), origin="lower", extent=km, cmap=diverging,
                     norm=TwoSlopeNorm(vcenter=0.0, vmin=low, vmax=high), interpolation="nearest")
    base(b, "B · Dönüş payı (dk) ve çizgiler")
    for rings, color, z in ((red, CRITICAL, 4), (yellow, WARNING, 5)):
        for ring in rings:
            if -MIN_DRAWN_HOLE_M2 < signed_area_m2(ring) < 0.0:
                continue  # a small hole: its cells are already grey in the mask
            b.plot(ring[:, 0] / 1000, ring[:, 1] / 1000, color=color, lw=1.6, path_effects=halo, zorder=z)
    bar = fig.colorbar(image, ax=b, shrink=0.82, pad=0.02)
    bar.set_label("dk · mavi: güvenli taraf, kırmızı: çizginin ötesi", color=INK_2)
    b.legend(handles=[Line2D([], [], color=CRITICAL, lw=2.0, path_effects=halo, label="kırmızı çizgi: pay = 0 (abort)"),
                      Line2D([], [], color=WARNING, lw=2.0, path_effects=halo,
                             label="sarı çizgi: pay = 30 dk (terminate)"),
                      Patch(facecolor=NEUTRAL, label="yasak veya erişilemez hücre")],
             loc="lower left", fontsize=8, frameon=True, facecolor=SURFACE, edgecolor="#e1e0d9")
    fig.suptitle(title,
                 x=0.01, ha="left", fontsize=12, color=INK)
    fig.text(0.01, 0.005, caption, ha="left", va="bottom", fontsize=7, color=MUTED, wrap=True)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", default=MANIFEST)
    parser.add_argument("--crew", default="config/crew.yaml")
    parser.add_argument("--suit", default="config/suit.yaml")
    parser.add_argument("--crew-id", default="EV1")
    parser.add_argument("--habitat-xy", type=float, nargs=2, default=(0.0, 0.0), metavar=("X", "Y"))
    parser.add_argument("--remaining-min", type=float, default=40.0,
                        help="SCENARIO snapshot: consumables left above reserve, in minutes of nominal use")
    parser.add_argument("--sigma-percentile", type=float, default=95.0)
    parser.add_argument("--out-root", default="data/derived/BXW")
    args = parser.parse_args()

    manifest_path = ROOT / args.manifest
    assets = json.loads(manifest_path.read_text(encoding="utf-8"))["assets"]
    recorded = {path: entry["sha256"] for path, entry in assets.items()}  # keyed by repo-relative path
    inputs = {}
    for name, rel in INPUTS.items():
        digest = sha256(ROOT / rel)
        if recorded.get(rel) != digest:
            raise SystemExit(f"{rel}: SHA256 {digest} does not match the accepted T1 manifest")
        inputs[name] = {"path": rel, "sha256": digest, "matches_manifest": True}

    dem4 = read_grid_order(ROOT / INPUTS["dem_plan_4m"], 4.0)
    dem1 = read_grid_order(ROOT / INPUTS["dem_enu"], 1.0)
    slope5 = read_grid_order(ROOT / INPUTS["slope_5m"], 1.0)
    slope2 = read_grid_order(ROOT / INPUTS["slope_2m"], 1.0)
    sigma1 = read_grid_order(ROOT / INPUTS["slope_sigma"], 1.0)
    if dem4.shape != (750, 750) or dem1.shape != (3000, 3000):
        raise SystemExit("unexpected grid shapes")

    slope = block_reduce(slope5, 4, "mean")
    sigma = block_reduce(sigma1, 4, "mean")  # any missing 1 m value keeps the 4 m cell missing
    wall = block_reduce(slope2, 4, "max")
    relief = block_detrended_relief(dem1, 4, 1.0)
    sigma_fallback = float(np.nanpercentile(sigma, args.sigma_percentile))
    origin = (-1500.0, -1500.0)
    grid = Grid(origin, 4.0, width=750, height=750, layers={
        "z_m": dem4, "slope_deg": slope, "slope_sigma_deg": sigma,
        "state": np.full((750, 750), UNOBSERVED, dtype=np.uint8), "relief_m": relief, "wall_slope_deg": wall,
    })

    walk, suit = load_models(ROOT / args.suit)
    crew = load_crew(ROOT / args.crew)[args.crew_id]
    timing = {}
    started = time.perf_counter()
    terrain = prepare_terrain(grid, walk, sigma_fallback_deg=sigma_fallback)
    timing["prepare_terrain_s"] = time.perf_counter() - started

    requested = grid.cell_index(*args.habitat_xy)
    started = time.perf_counter()
    labels = walkable_components(terrain)
    timing["components_s"] = time.perf_counter() - started
    habitat, component_info = nearest_in_largest_component(labels, requested)
    habitat_xy = grid.cell_center(*habitat)

    runs = []
    for _ in range(2):  # the second run is the steady state (numba compiled and cached)
        started = time.perf_counter()
        field = walkback(terrain, [habitat])
        runs.append(time.perf_counter() - started)
    timing["walkback_first_s"], timing["walkback_steady_s"] = runs

    nominal_speed = walk.speed_factor_unobserved * walking_speed(0.0, walk)
    nominal_power = metabolic_power(nominal_speed, 0.0, walk.eta_default, crew, suit, walk)
    rates = Rates.from_metabolic_power(nominal_power, suit)
    reserve = Resources(o2_kg=0.1, co2_capacity_kg=0.0, water_kg=0.0, battery_wh=0.0)  # FR-01 o2_res; others: no spec value
    budget_s = args.remaining_min * 60.0
    remaining = Resources(
        o2_kg=reserve.o2_kg + rates.o2_kg_s * budget_s,
        co2_capacity_kg=reserve.co2_capacity_kg + rates.co2_kg_s * budget_s,
        water_kg=reserve.water_kg + rates.water_kg_s * budget_s,
        battery_wh=reserve.battery_wh + rates.battery_w * budget_s / 3600.0,
    )
    started = time.perf_counter()
    margin = margin_for_crew(field, crew, suit, walk, remaining, reserve, rates)
    timing["margin_s"] = time.perf_counter() - started
    started = time.perf_counter()
    red = region_contours(margin.margin_s, origin, 4.0, 0.0)
    yellow = region_contours(margin.margin_s, origin, 4.0, 30 * 60.0)
    timing["contours_s"] = time.perf_counter() - started

    w_eps_min = field.time_eps_s() / 60.0
    unreachable = ~np.isfinite(field.time_s)
    out_dir = ROOT / args.out_root / f"t2-run-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    out_dir.mkdir(parents=True, exist_ok=False)
    png = out_dir / "margin_map_BXW_EV1.png"
    caption = (
        "Arazi: Gale DEM v3 (DERIVED, T1 kabul koşusu lfDo4ErT; SHA256 manifestle doğrulandı). 4 m ızgara; eğim = 1 m "
        "slope_5m blok ortalaması, σ = T1 ampirik eğim uyuşmazlığı vekili (bağımsız 1σ değil; eksik σ = "
        f"{args.sigma_percentile:g}. yüzdelik {sigma_fallback:.2f}°). SCENARIO: tüm hücreler UNOBSERVED (yalnız yörünge), "
        f"habitat ({habitat_xy[0]:.0f}, {habitat_xy[1]:.0f}) m, {crew.crew_id} W={crew.body_mass_kg:g} kg L={crew.load_mass_kg:g} kg, "
        f"kalan sarf = rezerv + {args.remaining_min:g} dk nominal tüketim, gün ışığı/kaya terimi yok. "
        "0,01 km²'den küçük delik halkaları çizilmedi; o hücreler gri maskededir."
    )
    plot(png, (origin[0], origin[0] + 3000.0, origin[1], origin[1] + 3000.0), w_eps_min, margin.margin_min,
         terrain.banned_mask | unreachable, habitat_xy, red, yellow, caption)

    def rings(items):
        areas = [signed_area_m2(r) for r in items]
        return {"rings": len(items), "outer": sum(a > 0 for a in areas), "holes": sum(a < 0 for a in areas),
                "holes_drawn_in_png": sum(a <= -MIN_DRAWN_HOLE_M2 for a in areas),
                "net_area_km2": sum(areas) / 1e6}

    limiting_counts = {LIM_NAMES.get(int(c), str(int(c))): int(n)
                       for c, n in zip(*np.unique(margin.limiting, return_counts=True))}
    summary = {
        "schema": "redline.t2_margin_map.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site_id": "BXW",
        "provenance_status": "SCENARIO",
        "status_note": "DERIVED terrain + SCENARIO crew/suit/resources/habitat; not a mission plan",
        "t1_manifest": {"path": args.manifest, "sha256": sha256(manifest_path)},
        "inputs": inputs,
        "parameters": {
            "crew_file": {"path": args.crew, "sha256": sha256(ROOT / args.crew)},
            "suit_file": {"path": args.suit, "sha256": sha256(ROOT / args.suit)},
            "crew": {"crew_id": crew.crew_id, "body_mass_kg": crew.body_mass_kg, "load_mass_kg": crew.load_mass_kg,
                     "theta": crew.theta},
            "walk": walk.__dict__, "suit": suit.__dict__,
            "risk": {"z_eps": 1.645, "sigma_theta": 0.2},
        },
        "planning_layers": {
            "grid": {"origin_xy_m": origin, "resolution_m": 4.0, "shape": [750, 750], "row0": "south"},
            "z_m": "dem_plan_4m (bilinear from source, T1)",
            "slope_deg": "mean of 1 m slope_5m over each 4x4 block",
            "slope_sigma_deg": "mean of 1 m slope_sigma; a block with any missing value is missing",
            "relief_m": "range of 1 m DEM residual after a least-squares plane per 4x4 block",
            "wall_slope_deg": "max of 1 m slope_2m per 4x4 block",
            "state": "UNOBSERVED everywhere (SCENARIO: orbital data only)",
        },
        "sigma": {"fallback_deg": sigma_fallback, "fallback_percentile": args.sigma_percentile,
                  "fallback_cells": terrain.sigma_fallback_cells,
                  "meaning": "T1 empirical slope disagreement proxy (deg), used as sigma_s; not an independent 1-sigma"},
        "habitat": {"requested_xy_m": list(args.habitat_xy), "cell": habitat, "xy_m": habitat_xy,
                    "shift_m": float(np.hypot(habitat_xy[0] - args.habitat_xy[0], habitat_xy[1] - args.habitat_xy[1])),
                    "rule": "nearest cell to the request inside the largest walkable component (edge rules)",
                    "walkable_components": component_info, "status": "SCENARIO"},
        "scenario_snapshot": {
            "remaining_minutes_above_reserve": args.remaining_min,
            "reserve": reserve.__dict__, "remaining": remaining.__dict__,
            "nominal_rates": rates.__dict__, "nominal_speed_m_s": nominal_speed, "nominal_power_w": nominal_power,
            "daylight": "not applied (needs T6 SPICE environment)", "rocks": "not applied (no rock layer yet)",
        },
        "stats": {
            "banned_fraction": float(terrain.banned_mask.mean()),
            "unreachable_fraction": float(unreachable.mean()),
            "w_eps_min": summary_stats(w_eps_min),
            "margin_min": summary_stats(margin.margin_min),
            "safe_fraction_margin_ge_0": float(np.mean(np.nan_to_num(margin.margin_s, nan=-np.inf) >= 0.0)),
            "limiting_cell_counts": limiting_counts,
        },
        "contours": {"red_margin_0": rings(red), "yellow_margin_30min": rings(yellow)},
        "timing_s": timing,
        "performance_target": "walkback 3x3 km at 4 m <= 1 s (proje.md §7.5)",
        "environment": {"python": platform.python_version(), "machine": platform.machine(),
                        "numpy": np.__version__, "rasterio": rasterio.__version__},
        "notes": list(terrain.notes),
        "outputs": {"png": {"path": str(png.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(png)}},
    }
    (out_dir / "t2_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"out_dir": str(out_dir.relative_to(ROOT)), "timing_s": timing, "stats": summary["stats"],
                      "contours": summary["contours"], "habitat": summary["habitat"]}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
