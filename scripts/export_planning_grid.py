"""Export the BXW 4 m planning grid for ROS nodes (proje.md §7.1, §8.3–8.4; D008–D010).

Reads only the T1-accepted products, checks each SHA-256 against the accepted
run manifest, builds the planning layers with redline_core and writes an
immutable ``<out>.npz`` + ``<out>.json`` (DERIVED). `cell_store` and
`walkback_field` load this file with numpy only. Run inside the REDLINE venv.

``--sigma-method ensemble`` (default, D010) averages the slopes of the two
processings of the same stereo pair and derives σ from their cell-scale
difference plus the stereo precision floor (config/terrain_uncertainty.yaml).
``t1-proxy`` reproduces the D008 layers (block mean of the T1 |Δslope| proxy).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
import yaml

from redline_core.grid import Grid, north_up_to_grid
from redline_core.planning import (
    build_planning_layers,
    ensemble_slope_layers,
    save_planning_grid,
    slope_floor_deg,
    stereo_expected_precision_m,
)
from redline_data.derive import slopes

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "data/stac/BXW/t1-run-lfDo4ErT/run_manifest.json"
INPUTS = {
    "dem_plan_4m": ("data/derived/BXW/dem_plan_4m.tif", 4.0),
    "dem_enu": ("data/derived/BXW/dem_enu.tif", 1.0),
    "slope_5m": ("data/derived/BXW/terrain/slope_5m.tif", 1.0),
    "slope_2m": ("data/derived/BXW/terrain/slope_2m.tif", 1.0),
    "slope_sigma": ("data/derived/BXW/comparison/slope_sigma.tif", 1.0),
    "aligned_reference": ("data/derived/BXW/comparison/aligned_reference.tif", 1.0),
}
EXPECTED_TRANSFORM = {4.0: (4.0, 0.0, -1500.0, 0.0, -4.0, 1500.0), 1.0: (1.0, 0.0, -1500.0, 0.0, -1.0, 1500.0)}


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", default=MANIFEST)
    parser.add_argument("--out", default="data/derived/BXW/planning/bxw_planning_4m_v2",
                        help="output stem (.npz and .json are added); existing files are never replaced")
    parser.add_argument("--sigma-method", choices=["ensemble", "t1-proxy"], default="ensemble")
    parser.add_argument("--uncertainty", default="config/terrain_uncertainty.yaml")
    args = parser.parse_args()

    manifest_path = ROOT / args.manifest
    recorded = {p: e["sha256"] for p, e in json.loads(manifest_path.read_text(encoding="utf-8"))["assets"].items()}
    inputs, arrays = {}, {}
    for name, (rel, resolution) in INPUTS.items():
        digest = sha256(ROOT / rel)
        if recorded.get(rel) != digest:
            raise SystemExit(f"{rel}: SHA256 {digest} does not match the accepted T1 manifest")
        inputs[name] = {"path": rel, "sha256": digest}
        arrays[name] = read_grid_order(ROOT / rel, resolution)
    if arrays["dem_plan_4m"].shape != (750, 750) or arrays["dem_enu"].shape != (3000, 3000):
        raise SystemExit("unexpected T1 grid shapes")

    layers = build_planning_layers(arrays["dem_plan_4m"], arrays["dem_enu"], arrays["slope_5m"],
                                   arrays["slope_2m"], arrays["slope_sigma"], 4, 1.0)
    sigma_record = {"method": "t1-proxy", "rule": "D008: block mean of the T1 |Δslope| proxy"}
    if args.sigma_method == "ensemble":
        config = yaml.safe_load((ROOT / args.uncertainty).read_text(encoding="utf-8"))["sites"]["BXW"]
        stereo = config["stereo"]
        ep = stereo_expected_precision_m(stereo["gsd_m"], *stereo["emission_deg"],
                                         opposite_sides=stereo["opposite_sides"],
                                         matching_px=stereo["matching_precision_px"])
        floor = slope_floor_deg(ep, config["slope_baseline_m"])
        reference_slope = slopes(arrays["aligned_reference"], 1.0, (config["slope_baseline_m"],))[
            float(config["slope_baseline_m"])]
        mu, sigma, info = ensemble_slope_layers(arrays["slope_5m"], reference_slope, 4,
                                                window_cells=int(config["window_cells"]), floor_deg=floor)
        layers["slope_deg"], layers["slope_sigma_deg"] = mu, sigma
        sigma_record = {"method": "two_processing_ensemble", "rule": "D010", "config": args.uncertainty,
                        "config_sha256": sha256(ROOT / args.uncertainty), "expected_precision_m": ep,
                        "floor_deg": floor, **info}
    grid = Grid((-1500.0, -1500.0), 4.0, width=750, height=750, layers=layers)
    provenance = {
        "status": "DERIVED",
        "site_id": "BXW",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "t1_manifest": {"path": args.manifest, "sha256": sha256(manifest_path)},
        "inputs": inputs,
        "rules": "docs/DECISIONS.md D008 planning layers (block mean/max, detrended relief)",
        "slope_and_sigma": sigma_record,
        "frame": "map (local ENU, metres); origin = south-west corner of cell (0, 0)",
        "note": "Terrain values are DERIVED from Gale DEM v3 (T1). The cell state is not stored.",
        "generator": "scripts/export_planning_grid.py",
    }
    sidecar = save_planning_grid(ROOT / args.out, grid, provenance)
    stats = {name: {"finite_fraction": float(np.isfinite(a).mean())} for name, a in layers.items()}
    print(json.dumps({"out": args.out, "npz_sha256": sidecar["npz_sha256"], "layers": stats}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
