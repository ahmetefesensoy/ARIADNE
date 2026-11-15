"""Export existing core M1 speeds and BXW spawn metadata for the Unreal EV1 client.

This does not reimplement the walking model. Placement/crew are SCENARIO;
elevation and the speed lookup table are DERIVED with input hashes.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import yaml
from redline_core.cost_human import walking_speed
from redline_core.field_model import ReturnFieldModel, load_eva
from redline_core.params import load_crew, load_models
from redline_core.planning import load_planning_grid

ROOT = Path(__file__).resolve().parents[1]


def main():
    inputs = ["config/suit.yaml", "config/crew.yaml", "config/eva.yaml",
              "data/derived/BXW/planning/bxw_planning_4m_v2.npz", "config/gameplay_preview.yaml"]
    walk, suit = load_models(ROOT / inputs[0])
    grid, meta = load_planning_grid(ROOT / inputs[3])
    model = ReturnFieldModel(grid, walk, suit, load_crew(ROOT / inputs[1]), load_eva(ROOT / inputs[2]))
    iy, ix = model.habitat_cell
    x, y = grid.cell_center(iy, ix)
    z = float(grid.layer("z_m")[iy, ix])
    # A nearby, reachable context-review marker for the orientation walkthrough.
    # It is explicitly SCENARIO and does not stand for a NASA sampling target.
    xx = grid.origin_xy[0] + (np.arange(grid.width) + .5) * grid.resolution_m
    yy = grid.origin_xy[1] + (np.arange(grid.height) + .5) * grid.resolution_m
    dist = np.hypot(xx[None, :] - x, yy[:, None] - y)
    candidate = np.isfinite(model.field.time_s) & (dist >= 12) & (dist <= 20)
    score = (xx[None, :] - (x + 16)) ** 2 + (yy[:, None] - y) ** 2
    sy, sx = np.unravel_index(np.argmin(np.where(candidate, score, np.inf)), score.shape)
    if not candidate[sy, sx]: raise RuntimeError("No reachable orientation station near habitat")
    station_xy = list(grid.cell_center(int(sy), int(sx)))
    grades = np.linspace(-np.tan(np.deg2rad(walk.slope_max_deg)),
                         np.tan(np.deg2rad(walk.slope_max_deg)), 257)
    result = {
        "schema": "redline.eva.runtime.v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "site_id": "BXW", "crew_id": "EV1", "placement_status": "SCENARIO",
        "movement_table_status": "DERIVED", "source": "redline_core.cost_human.walking_speed (M1)",
        "note": "Core-generated speed lookup; live QueryCell supplies the state speed factor. Not suit hardware validation.",
        "spawn_map_xyz_m": [x, y, z], "habitat_cell": [int(iy), int(ix)],
        "intro": {"status": "SCENARIO", "habitat_xy_m": [x, y], "briefing_xy_m": [x-6, y-2],
                  "station_xy_m": station_xy, "interaction_radius_m": 4.,
                  "note": "Orientation context review only; not a science product or archive sample."},
        "gravity_m_s2": walk.g_mars_m_s2, "max_slope_deg": walk.slope_max_deg,
        "gameplay_locomotion": yaml.safe_load((ROOT / inputs[4]).read_text()),
        "unobserved_speed_factor": walk.speed_factor_unobserved,
        "walking_speed_samples": np.column_stack((grades, walking_speed(grades, walk))).tolist(),
        "inputs": [{"path": p, "sha256": hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in inputs],
        "planning_grid_sha256": meta["npz_sha256"],
    }
    path = ROOT / "data/engines/BXW/eva-runtime-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    stable = lambda value: {k: v for k, v in value.items() if k != "created_at_utc"}
    if old is None or stable(old) != stable(result):
        path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(path), "spawn_map_xyz_m": result["spawn_map_xyz_m"],
                      "flat_unobserved_speed_m_s": walking_speed(0, walk) * walk.speed_factor_unobserved}))


if __name__ == "__main__":
    main()
