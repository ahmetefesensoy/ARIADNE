"""Run with Blender --background --disable-autoexec --python <this file>."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sources = {
    "astronaut": next((ROOT / "incoming/astronaut/animations").rglob("model.glb")),
    "rover_1": next((ROOT / "incoming/rover_1/tripo").rglob("model.glb")),
    "scout_1": ROOT / "incoming/scout_1/source.glb",
    "pr_1": ROOT / "incoming/pr_1/source.glb",
    "habitat": ROOT / "incoming/habitat/source.glb",
    "sample_tube": ROOT / "incoming/sample_tube/source.stl",
    "science_station": next((ROOT / "incoming/science_station/tripo").rglob("model.glb")),
    "rock_07": ROOT / "incoming/rock_07/source.gltf",
    "rock_09": ROOT / "incoming/rock_09/source.gltf",
    "curiosity_reference": ROOT / "incoming/curiosity_reference/source.blend",
}
report = {}
for key, path in sources.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if path.suffix == ".blend":
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            dst.objects = src.objects
        for obj in dst.objects:
            if obj and not obj.users_collection:
                bpy.context.scene.collection.objects.link(obj)
    elif path.suffix == ".stl":
        bpy.ops.wm.stl_import(filepath=str(path))
    else:
        bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    report[key] = {"source": str(path.relative_to(ROOT)), "meshes": [], "actions": [a.name for a in bpy.data.actions], "armatures": [{"name": o.name, "bones": len(o.data.bones)} for o in bpy.context.scene.objects if o.type == "ARMATURE"]}
    for o in meshes:
        points = [o.matrix_world @ Vector(v) for v in o.bound_box]
        low = [min(p[i] for p in points) for i in range(3)]
        high = [max(p[i] for p in points) for i in range(3)]
        o.data.calc_loop_triangles()
        report[key]["meshes"].append({"name": o.name, "triangles": len(o.data.loop_triangles), "min": low, "max": high, "center": [(a+b)/2 for a,b in zip(low,high)], "dimensions": [b-a for a,b in zip(low,high)], "materials": [m.name if m else None for m in o.data.materials]})
    print(key, len(meshes), sum(m["triangles"] for m in report[key]["meshes"]), flush=True)
target = ROOT / "production/source_inventory.json"
target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("WROTE", target, flush=True)
