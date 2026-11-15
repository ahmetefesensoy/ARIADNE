"""Tablet remote-mapping atlas for BXW (user request 2026-11-15; Space Apps "Martian Map" core).

Builds north-up 2048 px layers over the 3 x 3 km map frame ([-1500, 1500] m, 1.465 m/px) and one
manifest the game tablet reads:

- imagery: HiRISE 78-quad colour basemap (atlas_context.png of surface-v1; DERIVED, credit in manifest)
- hillshade: from the 1 m HiRISE DTM (dem_enu.tif; DERIVED)
- slope_class: walkable < 15 deg, caution 15-25 deg, no-go >= 25 deg (FR-08 limit; DERIVED, SCENARIO limits)
- science_units: TPI ridge / hollow on the 1 m DTM, annulus 5-25 m (targets_v1 rule); shown where
  |TPI| >= 1 m, because 0.3 m (the target eligibility floor) marks almost every metre (DERIVED)
- return_time: risk-adjusted walk back to the habitat T_eps at EVA start as contour lines at
  10/30/45/60 min, the 20 min SEP shelter limit (FR-03) as a thick red line over a light fill
  (DERIVED from the planning walk model)
- stations: the science campaign (config/science_campaign_BXW.yaml) resolved on the grid, with
  distance, path length, walk time, T_eps, slope and every task's purpose (tr/en)

Stations must stand on walkable ground (finite return time, slope below the walkable limit); the
script fails otherwise. Run inside the REDLINE venv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.signal import fftconvolve

from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid
from redline_core.science_campaign import load_campaign

ROOT = Path(__file__).resolve().parents[1]
HALF = 1500.0
SIZE = 2048
PX = 2 * HALF / SIZE
WALKABLE_DEG, NOGO_DEG = 15.0, 25.0
BANDS_MIN = (10.0, 20.0, 30.0, 45.0, 60.0)
UNIT_TPI_M = 1.0
CONTOURS = ((10.0, (255, 255, 255, 230), 1), (20.0, (255, 40, 40, 255), 3), (30.0, (255, 255, 255, 200), 1),
            (45.0, (255, 255, 255, 170), 1), (60.0, (255, 255, 255, 140), 1))  # minutes, colour, half-width px
ROLE_RGB = {"control": (70, 160, 255), "test": (255, 120, 40), "infrastructure": (230, 230, 230)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def to_image(grid_array: np.ndarray) -> np.ndarray:
    """Planning-grid array [iy, ix] (iy northward) to a north-up image of SIZE x SIZE (nearest)."""
    north_up = np.flipud(grid_array)
    idx = (np.arange(SIZE) * north_up.shape[0] / SIZE).astype(int)
    return north_up[np.ix_(idx, idx)]


def px(x: float, y: float) -> tuple[float, float]:
    return (x + HALF) / PX, (HALF - y) / PX


def hillshade(z: np.ndarray, res: float, az_deg: float = 315.0, el_deg: float = 45.0) -> np.ndarray:
    dz_dy, dz_dx = np.gradient(z, res)  # rows run south (north-up raster)
    slope = np.arctan(np.hypot(dz_dx, dz_dy))
    aspect = np.arctan2(-dz_dx, dz_dy)
    az, el = math.radians(360.0 - az_deg + 90.0), math.radians(el_deg)
    shade = np.sin(el) * np.cos(slope) + np.cos(el) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(np.nan_to_num(shade, nan=0.0), 0, 1)


def resize(a: np.ndarray, mode=Image.BILINEAR) -> np.ndarray:
    return np.asarray(Image.fromarray(a.astype(np.float32), mode="F").resize((SIZE, SIZE), mode))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="data/engines/BXW/tablet-atlas-v1")
    parser.add_argument("--preview", default="docs/verification/TABLET_ATLAS_PREVIEW.png")
    parser.add_argument("--report", default="docs/verification/TABLET_ATLAS.json")
    args = parser.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    layers = {}

    # imagery (HiRISE colour basemap, already in the map frame)
    imagery_src = ROOT / "data/engines/BXW/surface-v1/atlas_context.png"
    Image.MAX_IMAGE_PIXELS = None
    Image.open(imagery_src).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS).save(out / "imagery.png")
    layers["imagery"] = {"file": "imagery.png", "status": "DERIVED", "source": str(imagery_src.relative_to(ROOT)),
                         "credit": "HiRISE 78-quad colour basemap: T. J. Parker and F. J. Calef III; "
                                   "NASA/JPL-Caltech, USGS Astrogeology, University of Arizona",
                         "limits": "grey strips are provider HiRISE RED-only areas without colour; lighting is baked "
                                   "into the mosaic; not newly measured"}

    # 1 m DTM: hillshade and TPI science units
    dem_path = ROOT / "data/derived/BXW/dem_enu.tif"
    with rasterio.open(dem_path) as dem:
        z = dem.read(1).astype(np.float64)
        bounds = [round(v, 3) for v in dem.bounds]
        res = dem.res[0]
        if dem.nodata is not None:
            z[z == dem.nodata] = np.nan
    if bounds != [-HALF, -HALF, HALF, HALF]:
        raise SystemExit(f"DTM bounds {bounds} are not the 3 km map frame")
    shade = resize(hillshade(z, res))
    Image.fromarray((shade * 255).astype(np.uint8), mode="L").save(out / "hillshade.png")
    layers["hillshade"] = {"file": "hillshade.png", "status": "DERIVED", "source": str(dem_path.relative_to(ROOT)),
                           "sun": {"azimuth_deg": 315, "elevation_deg": 45, "note": "cartographic light, not the EVA sun"}}
    reach = int(math.ceil(25.0 / res))
    yy, xx = np.mgrid[-reach:reach + 1, -reach:reach + 1] * res
    kernel = ((np.hypot(yy, xx) > 5.0) & (np.hypot(yy, xx) <= 25.0)).astype(float)
    valid = np.isfinite(z)
    num = fftconvolve(np.where(valid, z, 0.0), kernel, mode="same")
    den = fftconvolve(valid.astype(float), kernel, mode="same")
    with np.errstate(invalid="ignore", divide="ignore"):
        tpi = z - num / den
    tpi[(den < 0.5 * kernel.sum()) | ~valid] = np.nan
    tpi_img = resize(np.nan_to_num(tpi, nan=0.0))
    units = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    units[tpi_img >= UNIT_TPI_M] = (230, 120, 50, 120)   # ridge
    units[tpi_img <= -UNIT_TPI_M] = (40, 150, 230, 120)  # hollow
    Image.fromarray(units, mode="RGBA").save(out / "science_units.png")
    layers["science_units"] = {"file": "science_units.png", "status": "DERIVED",
                               "rule": f"TPI on the 1 m DTM, annulus 5-25 m; ridge >= +{UNIT_TPI_M} m, "
                                       f"hollow <= -{UNIT_TPI_M} m",
                               "legend": {"ridge": [230, 120, 50], "hollow": [40, 150, 230]},
                               "note": "terrain position only; composition is not observed from orbit here"}

    # planning grid: slope classes and the return field
    grid, meta = load_planning_grid(ROOT / "data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    walk, suit = load_models(ROOT / "config/suit.yaml")
    eva = load_eva(ROOT / "config/eva.yaml")
    model = ReturnFieldModel(grid, walk, suit, load_crew(ROOT / "config/crew.yaml"), eva)
    field = model.field
    t_eps = field.time_eps_s(eva.z_eps, eva.sigma_theta) / 60.0
    slope = np.asarray(grid.layer("slope_deg"), dtype=float)
    slope_img = to_image(slope)
    sc = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    sc[slope_img >= WALKABLE_DEG] = (240, 190, 40, 120)
    sc[(slope_img >= NOGO_DEG) | ~np.isfinite(to_image(t_eps))] = (200, 40, 40, 150)
    Image.fromarray(sc, mode="RGBA").save(out / "slope_class.png")
    layers["slope_class"] = {"file": "slope_class.png", "status": "DERIVED",
                             "rule": f"caution >= {WALKABLE_DEG} deg, no-go >= {NOGO_DEG} deg or no walk home "
                                     "(4 m planning grid)", "limits_status": "SCENARIO (FR-08)"}
    t_img = to_image(t_eps)
    rt = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    rt[np.isfinite(t_img) & (t_img <= 20.0)] = (60, 200, 90, 45)  # reachable within the SEP limit
    for minutes, rgba, half in CONTOURS:
        inside = np.isfinite(t_img) & (t_img <= minutes)
        line = (inside ^ np.roll(inside, 1, 0)) | (inside ^ np.roll(inside, 1, 1))
        rt[ndimage.binary_dilation(line, iterations=half)] = rgba
    Image.fromarray(rt, mode="RGBA").save(out / "return_time.png")
    layers["return_time"] = {"file": "return_time.png", "status": "DERIVED",
                             "quantity": "risk-adjusted walk back to the habitat T_eps (z 1.645, sigma_theta 0.2) at EVA "
                                         "start; the live red line still comes from ROS",
                             "contours_min": [c[0] for c in CONTOURS], "sep_shelter_limit_min": 20.0,
                             "contour_rgba": [list(c[1]) for c in CONTOURS]}

    # stations
    campaign = load_campaign(ROOT / "config/science_campaign_BXW.yaml",
                             ROOT / "data/derived/BXW/planning/targets_v1.json", root=ROOT)
    hx, hy = model.habitat_xy
    stations, problems = [], []
    for s in campaign.stations:
        cell = model.cell_of(s.xy_m)
        row, col = int(round((HALF - s.xy_m[1]) / res - 0.5)), int(round((s.xy_m[0] + HALF) / res - 0.5))
        info = {"id": s.station_id, "role": s.role, "science_class": s.science_class, "target_id": s.target_id,
                "xy_m": list(s.xy_m), "z_m": round(float(z[row, col]), 2),
                "straight_m": round(math.hypot(s.xy_m[0] - hx, s.xy_m[1] - hy), 1),
                "name": s.name, "purpose": s.purpose,
                "tasks": [{"id": t, "spec": campaign.tasks[t].spec, "action": campaign.tasks[t].action,
                           "actor": campaign.tasks[t].actor, "asset": campaign.tasks[t].asset,
                           "duration_min": campaign.tasks[t].duration_min, "data_status": campaign.tasks[t].data_status,
                           "data_note": campaign.tasks[t].data_note, "purpose": campaign.tasks[t].purpose}
                          for t in s.tasks]}
        if cell is None:
            problems.append(f"{s.station_id}: outside the grid")
        else:
            eps, mu, path_m, sl = (float(a[cell]) for a in (t_eps, field.time_s / 60.0, field.distance_m, slope))
            info.update({"cell": list(cell), "path_m": round(path_m, 1) if math.isfinite(path_m) else None,
                         "walk_mu_min": round(mu, 2) if math.isfinite(mu) else None,
                         "t_eps_min": round(eps, 2) if math.isfinite(eps) else None, "slope_deg": round(sl, 1),
                         "inside_sep_limit": bool(math.isfinite(eps) and eps <= 20.0)})
            robot_only = all(campaign.tasks[t].actor not in ("EV1", "EV2") for t in s.tasks)
            if not robot_only and not (math.isfinite(eps) and sl < WALKABLE_DEG):
                problems.append(f"{s.station_id}: crew task on unwalkable ground (T_eps {eps:.1f} min, slope {sl:.1f} deg)")
        stations.append(info)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    # station overlay + composite preview
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    cx, cy = px(hx, hy)
    draw.rectangle([cx - 14, cy - 14, cx + 14, cy + 14], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=3)
    draw.text((cx + 20, cy + 8), "HAB", fill=(255, 255, 255, 255), font=font, stroke_width=3, stroke_fill=(0, 0, 0, 255))
    for st in stations:
        if st["id"] == "ST-LAB":
            continue  # inside the habitat
        x, y = px(*st["xy_m"])
        color = ROLE_RGB[st["role"]] + (255,)
        draw.ellipse([x - 16, y - 16, x + 16, y + 16], fill=color, outline=(0, 0, 0, 255), width=4)
        draw.text((x + 22, y - 18), st["id"], fill=color, font=font, stroke_width=3, stroke_fill=(0, 0, 0, 255))
    overlay.save(out / "stations.png")
    layers["stations"] = {"file": "stations.png", "status": "SCENARIO", "legend": {k: list(v) for k, v in ROLE_RGB.items()}}
    base = Image.open(out / "imagery.png").convert("RGBA")
    shade_rgba = Image.open(out / "hillshade.png").convert("RGBA")
    shade_rgba.putalpha(50)
    base = Image.alpha_composite(base, shade_rgba)
    previews = {"safety": ("return_time", "stations"), "science": ("science_units", "stations")}
    for view, names in previews.items():
        composite = base
        for name in names:
            composite = Image.alpha_composite(composite, Image.open(out / layers[name]["file"]).convert("RGBA"))
        composite.save(out / f"composite_{view}.png")
        preview = ROOT / args.preview.replace(".png", f"_{view}.png")
        composite.convert("RGB").resize((1024, 1024), Image.LANCZOS).save(preview, optimize=True)

    manifest = {"schema": "redline.tablet_atlas.v1", "site_id": "BXW", "frame": "map", "units": "m",
                "bounds_map_m": [-HALF, -HALF, HALF, HALF], "size_px": SIZE, "m_per_px": PX, "north_up": True,
                "pixel_of": "col = (x + 1500) / m_per_px, row = (1500 - y) / m_per_px",
                "habitat_xy_m": [round(hx, 2), round(hy, 2)],
                "question": campaign.question, "mission_brief": campaign.mission_brief,
                "layers": {k: {**v, "sha256": sha256(out / v["file"])} for k, v in layers.items()},
                "stations": stations,
                "inputs": {"dem_sha256": sha256(dem_path), "planning_grid_sha256": meta.get("npz_sha256"),
                           "campaign_sha256": sha256(ROOT / "config/science_campaign_BXW.yaml")},
                "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / args.report).write_text(json.dumps({k: manifest[k] for k in manifest if k != "layers"} |
                                               {"layers": {k: {kk: vv for kk, vv in v.items()} for k, v in
                                                           manifest["layers"].items()},
                                                "atlas_dir": args.out,
                                                "previews": [args.preview.replace(".png", f"_{v}.png")
                                                             for v in ("safety", "science")]},
                                               indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for st in stations:
        print(st["id"], st["role"], st["science_class"], st["xy_m"], "straight", st["straight_m"], "path",
              st.get("path_m"), "Teps", st.get("t_eps_min"), "slope", st.get("slope_deg"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
