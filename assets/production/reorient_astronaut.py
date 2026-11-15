"""Turn the astronaut master to the documented +X-forward convention and re-export.

Usage: blender --background --factory-startup --python reorient_astronaut.py
build_package.py rotated the Tripo character by -90° about Z, which left it facing -Y
(its "front" preview showed a profile). Every hierarchy root (the ROOT empty with the
armature and skinned LODs, the unparented Gazebo copy and the capsule) is rotated +90°
about world Z. Textures are untouched. Nothing is saved unless the head ends up ahead of
the body's bounding-box centre along +X (the backpack sits behind). Afterwards run
rig_previews.py and inspect_variants.py unchanged to refresh clip FBX files and previews.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).parent))
from build_package import export_fbx, select, write_obj  # noqa: E402
from preview import bounds, views  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "incoming/astronaut"


def head_x(armature) -> float:
    bone = next(b for b in armature.data.bones if "head" in b.name.lower())
    return (armature.matrix_world @ bone.head_local).x


def main() -> None:
    meta = FOLDER / "asset.json"
    data = json.loads(meta.read_text(encoding="utf-8"))
    if any(r.get("kind") == "reorient_plus_x" for r in data.get("revisions", [])):
        raise SystemExit("astronaut is already reoriented")
    bpy.ops.wm.open_mainfile(filepath=str(FOLDER / "master.blend"), load_ui=False, use_scripts=False)
    objects = list(bpy.context.scene.objects)
    lod0 = [o for o in objects if o.type == "MESH" and o.name == "SK_Astronaut_LOD0"]
    arms = [o for o in objects if o.type == "ARMATURE"]
    collisions = [o for o in objects if o.type == "MESH" and o.name.startswith("UCX_")]
    lods = {level: [o for o in objects if o.type == "MESH" and o.name.endswith(f"LOD{level}")] for level in (1, 2)}
    gazebo = [o for o in objects if o.type == "MESH" and o.name.endswith("Gazebo")]
    lo, hi = bounds(lod0)
    before = {"head_x_minus_centre_x": head_x(arms[0]) - (lo.x + hi.x) / 2, "dimensions_m": list(hi - lo)}

    rotation = Matrix.Rotation(math.pi / 2, 4, "Z")
    for o in objects:
        if o.parent is None:
            o.matrix_world = rotation @ o.matrix_world
    bpy.context.view_layer.update()
    lo, hi = bounds(lod0)
    after = {"head_x_minus_centre_x": head_x(arms[0]) - (lo.x + hi.x) / 2, "dimensions_m": list(hi - lo)}
    if not after["head_x_minus_centre_x"] > 0.01:
        raise SystemExit(f"head is not ahead of the body along +X after rotation: {after}")
    bpy.ops.wm.save_as_mainfile(filepath=str(FOLDER / "master.blend"))

    for a in arms:
        a.data.pose_position = "POSE"
    export_fbx(FOLDER / "unreal/astronaut_LOD0.fbx", lod0 + arms + collisions, animate=True)
    for level, copies in lods.items():
        export_fbx(FOLDER / f"unreal/astronaut_LOD{level}.fbx", copies + arms, animate=False)
    select(lod0 + arms)
    bpy.ops.export_scene.gltf(filepath=str(FOLDER / "presentation.glb"), export_format="GLB", use_selection=True,
                              export_animations=True, export_def_bones=False)
    for a in arms:
        a.data.pose_position = "REST"
    write_obj(FOLDER / "gazebo/assembly.obj", gazebo)
    write_obj(FOLDER / "gazebo/collision.obj", collisions)
    for o in lods[1] + lods[2] + gazebo + collisions:
        o.hide_set(True)
    views(lod0, FOLDER / "preview", ("perspective", "front", "side", "back"), 640)
    arms[0].data.pose_position = "POSE"
    bpy.context.scene.frame_set(15)
    bpy.context.view_layer.update()
    views(lod0, FOLDER / "preview/animation", ("perspective", "back"), 640)
    arms[0].data.pose_position = "REST"

    old = Matrix(data["master"]["source_to_master_matrix"])
    data["master"]["source_to_master_matrix"] = [list(row) for row in rotation @ old]
    data["master"]["dimensions_m"] = after["dimensions_m"]
    data.setdefault("revisions", []).append({
        "kind": "reorient_plus_x", "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reason": "Master faced -Y (front preview showed a profile); rotated +90° about Z to the documented "
                  "+X forward / +Y left / +Z up convention used by every robot package.",
        "check_before": before, "check_after": after,
        "re_exported": ["unreal/astronaut_LOD0.fbx", "unreal/astronaut_LOD1.fbx", "unreal/astronaut_LOD2.fbx",
                        "presentation.glb", "gazebo/assembly.obj", "gazebo/collision.obj", "preview/*"],
        "script": "production/reorient_astronaut.py; then production/rig_previews.py and inspect_variants.py",
        "unchanged": "textures, skin weights, bone hierarchy, gazebo/parts local-space OBJ"})
    meta.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("REORIENTED", json.dumps({"before": before, "after": after}), flush=True)


if __name__ == "__main__":
    main()
