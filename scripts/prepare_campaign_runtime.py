"""Stage SCENARIO target/spawn positions on the existing verified T1 collision mesh.

Raw terrain and authored chemistry are preserved. Absolute referenced artifact
paths allow a small per-run manifest without copying gigabytes of terrain.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import math
import yaml
from redline_core.planning import load_planning_grid
from redline_core.campaign_sites import select_field_points
from redline_core.field_model import ReturnFieldModel,load_eva
from redline_core.params import load_crew,load_models
from redline_core.walkback import return_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--terrain", type=Path, default=Path.home()/".cache/redline/t3/terrain-bxw-v2/manifest.json")
    parser.add_argument("--profile",choices=("tutorial","field"),default="tutorial")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.terrain.read_text())
    for mesh in manifest["meshes"]:
        for key in ("relative_path", "visual_relative_path", "collision_relative_path"):
            if key in mesh: mesh[key] = str((args.terrain.parent / mesh[key]).resolve())
        mesh["collision_uri"] = Path(mesh.get("collision_relative_path", mesh["relative_path"])).as_uri()
    for artifact in manifest.get("artifacts", []):
        artifact["relative_path"] = str((args.terrain.parent / artifact["relative_path"]).resolve())
    for key in ("image", "yaml"):
        manifest["nav"][key] = str((args.terrain.parent / manifest["nav"][key]).resolve())
    helper_path = root/"ros_ws/src/redline_gazebo/scripts/prepare_world.py"
    module_spec = importlib.util.spec_from_file_location("redline_campaign_terrain", helper_path)
    helper = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(helper)
    grid, meta = load_planning_grid(root/"data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    targets = yaml.safe_load((root/"config/targets_BXW.yaml").read_text())
    field_model=None
    if args.profile=="field":
        walk,suit=load_models(root/"config/suit.yaml")
        eva=load_eva(root/"config/eva.yaml")
        field_model=ReturnFieldModel(grid,walk,suit,load_crew(root/"config/crew.yaml"),eva)
        times=field_model.field.time_eps_s(eva.z_eps,eva.sigma_theta)
        authored=select_field_points(grid,times,field_model.habitat_xy,[tile["bounds_map_m"] for tile in manifest["meshes"] if tile.get("role")=="ops_1m"])
        for target in targets["targets"]:target["point_m"][:2]=authored[target["id"]]
        targets["profile"]="field"
        targets["placement_note"]="SCENARIO 280–430 m field chapter within real 12–18 min return band; ridge/hollow names are narrative classes, not independently verified geology. Rover starts predeployed near ridge, not teleported during EVA."
    checks = []
    for target in targets["targets"]:
        x, y = target["point_m"][:2]
        iy, ix = grid.cell_index(x, y)
        target["point_m"][2] = float(helper.terrain_height(manifest, x, y))
        slope=float(grid.layer("slope_deg")[iy, ix])
        if not math.isfinite(slope) or slope>=25:raise ValueError("authored field point lacks walkable terrain support")
        if field_model is not None:
            path=return_path(field_model.field,(iy,ix))
            if not path:raise ValueError("field point has no supported return route")
            target["route_xy_m"]=[list(grid.cell_center(*cell)) for cell in reversed(path)]
            target["return_eps_min"]=float(times[iy,ix]/60.)
        checks.append({"id": target["id"], "point_m": target["point_m"],
                       "grid_slope_deg": float(grid.layer("slope_deg")[iy, ix]),"return_eps_min":target.get("return_eps_min")})
    x,y=(targets["targets"][0]["point_m"][0]-10.,targets["targets"][0]["point_m"][1]) if args.profile=="field" else (296.,-454.)
    ground = float(helper.terrain_height(manifest, x, y))
    manifest["spawn"] = {"map_x_m": x, "map_y_m": y, "ground_z_m": ground, "yaw_rad": 0.}
    goal = targets["targets"][0]["point_m"]
    manifest["goal"] = {"map_x_m": goal[0]-3., "map_y_m": goal[1],
                        "ground_z_m": float(helper.terrain_height(manifest, goal[0]-3., goal[1])), "yaw_rad": 0.}
    manifest["campaign_placement"] = {"status": "SCENARIO", "source_manifest": str(args.terrain),
        "source_sha256": hashlib.sha256(args.terrain.read_bytes()).hexdigest(),
        "note": "Authored predeployed rover spawn near field target (field profile) or habitat (tutorial); elevations sampled from existing verified collision triangles."}
    targets["coordinate_support"] = {"status": "DERIVED", "source_grid_sha256": meta["npz_sha256"],
        "source_terrain_sha256": manifest["campaign_placement"]["source_sha256"],
        "note": "XY and chemistry SCENARIO; Z from the same collision triangles used by Gazebo."}
    (args.out/"targets_BXW.yaml").write_text(yaml.safe_dump(targets, sort_keys=False, allow_unicode=True))
    (args.out/"terrain.json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n")
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "targets": checks,
              "spawn": manifest["spawn"], "status": "SCENARIO", "source": manifest["campaign_placement"]}
    scout_spec=importlib.util.spec_from_file_location("redline_scout_model",root/"ros_ws/src/redline_description/scripts/generate_scout.py")
    scout_helper=importlib.util.module_from_spec(scout_spec);scout_spec.loader.exec_module(scout_helper)
    sx,sy=330.,-474.
    scout_ground=float(helper.terrain_height(manifest,sx,sy))
    (args.out/"scout_1.sdf").write_text(scout_helper.model_sdf(sx,sy,scout_ground+.2))
    scout={"status":"SCENARIO","origin_map_xyz_m":[sx,sy,scout_ground],"ground_z_m":scout_ground,
           "note":"Original four-rotor physics; visual mesh is independent; Mars flight parameters are SCENARIO."}
    (args.out/"scout_1.json").write_text(json.dumps(scout,indent=2)+"\n")
    report["scout"]=scout
    (args.out/"placement.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps(report))


if __name__ == "__main__": main()
