"""Keep original drone; create a bounded-size derivative for Tripo segmentation."""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "incoming/scout_1/source.glb"))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
obj.data.calc_loop_triangles()
before = len(obj.data.loop_triangles)
mod = obj.modifiers.new("Bounded_segmentation_input", "DECIMATE")
mod.ratio = 55000 / before
bpy.ops.object.modifier_apply(modifier=mod.name)
for img in bpy.data.images:
    if img.size[0] > 2048 or img.size[1] > 2048:
        factor = 2048 / max(img.size)
        img.scale(round(img.size[0] * factor), round(img.size[1] * factor))
out = ROOT / "incoming/scout_1/processing"
out.mkdir(exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(out / "segmentation_input.glb"), export_format="GLB", use_selection=True, export_animations=False)
obj.data.calc_loop_triangles()
print("DRONE", before, "->", len(obj.data.loop_triangles), "triangles", flush=True)
