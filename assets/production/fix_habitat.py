"""Fix the habitat package's gaps and faceted look for game engines (user request, 2026-11-15).

Usage (always from the untouched source, so a rerun never thickens the shell twice):
    blender --background --disable-autoexec assets/incoming/habitat/master_v1_before_fix.blend \
            --python assets/production/fix_habitat.py
The first run on the original master.blend copies it to master_v1_before_fix.blend first.
The result is saved as master.blend next to it.

Audit before (Blender, backface culling as Unreal draws): the NASA HDU low-res shell had 130 open
boundary loops, 687 coincident (split) vertices and single-sided panels (window frames, waist ring,
tunnel door frame), so engines showed holes; FBX was exported without smoothing groups, so Unreal
recomputed hard normals and the curved shells looked boxy.

Fix per part and LOD: weld split vertices (0.5 mm), outward normals; LOD1/LOD2 are collapse-decimated
copies of the welded LOD0 (ratios 0.5/0.25, as the original package); then a 2 cm Solidify with rims
(no single-sided surface left), smooth shading by angle (40 deg, sharp edges kept) and face-area
weighted normals, all applied. The existing LOD1/LOD2 objects keep their names and get the new mesh.
FBX gets smoothing groups (mesh_smooth_type FACE) and tangent space. Originals are kept as
master_v1_before_fix.blend and unreal/v1_before_fix/. Visual SCENARIO asset; NASA source terms
in SOURCE.md still apply.
"""
import json
import math
import shutil
from pathlib import Path

import bmesh
import bpy

SOURCE = Path(bpy.data.filepath)
PKG = SOURCE.parent
WELD_M, SHELL_M, SMOOTH_DEG = 0.0005, 0.02, 40.0
LOD_RATIOS = {1: 0.5, 2: 0.25}
MARK = "redline_habitat_fix"


def backup() -> None:
    old = PKG / "master_v1_before_fix.blend"
    if not old.exists():
        shutil.copy2(PKG / "master.blend", old)
    keep = PKG / "unreal" / "v1_before_fix"
    keep.mkdir(exist_ok=True)
    for f in (PKG / "unreal").glob("habitat_LOD*.fbx"):
        if not (keep / f.name).exists():
            shutil.copy2(f, keep / f.name)


def audit(obj) -> dict:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    out = {"triangles": sum(len(f.verts) - 2 for f in bm.faces),
           "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
           "nonmanifold_edges": sum(1 for e in bm.edges if not e.is_manifold)}
    bm.free()
    return out


def weld(mesh, scale: float) -> int:
    bm = bmesh.new()
    bm.from_mesh(mesh)
    count = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=WELD_M / scale)
    count -= len(bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    return count


def build(mesh, matrix, ratio: float):
    """Decimate (ratio < 1), shell and smooth a copy of `mesh` on a temporary visible object."""
    tmp = bpy.data.objects.new("_fix_tmp", mesh.copy())
    bpy.context.scene.collection.objects.link(tmp)
    tmp.matrix_world = matrix
    bpy.context.view_layer.objects.active = tmp
    for o in bpy.context.view_layer.objects:
        o.select_set(o == tmp)
    scale = max(matrix.to_scale())
    if ratio < 1.0:
        dec = tmp.modifiers.new("lod", "DECIMATE")
        dec.decimate_type, dec.ratio = "COLLAPSE", ratio
        bpy.ops.object.modifier_apply(modifier=dec.name)
    solid = tmp.modifiers.new("shell", "SOLIDIFY")
    solid.thickness, solid.offset = SHELL_M / scale, -1.0
    solid.use_rim, solid.use_even_offset, solid.use_quality_normals = True, True, True
    bpy.ops.object.modifier_apply(modifier=solid.name)
    bpy.ops.object.shade_auto_smooth(angle=math.radians(SMOOTH_DEG))
    weighted = tmp.modifiers.new("weighted", "WEIGHTED_NORMAL")
    weighted.keep_sharp, weighted.mode = True, "FACE_AREA"
    for m in list(tmp.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    data = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    return data


def export(path: Path, objects) -> None:
    state = {o: (o.hide_viewport, o.hide_get()) for o in objects}
    for o in objects:
        o.hide_viewport = False
        o.hide_set(False)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objects)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"}, global_scale=1,
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y",
                             axis_up="Z", use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True,
                             add_leaf_bones=False, path_mode="COPY", embed_textures=False)
    for o, (viewport, hidden) in state.items():
        o.hide_viewport = viewport
        o.hide_set(hidden)


def main() -> None:
    if bpy.context.scene.get(MARK):
        raise SystemExit(f"{SOURCE.name} is already fixed; run on master_v1_before_fix.blend")
    backup()
    parts = [o for o in bpy.data.objects if o.type == "MESH" and o.name.endswith("_LOD0")]
    report = {"parts": {}, "lods": {}}
    by_level = {0: list(parts), 1: [], 2: []}
    for lod0 in parts:
        before = audit(lod0)
        source = lod0.data.copy()
        welded = weld(source, max(lod0.matrix_world.to_scale()))
        for level, ratio in ((0, 1.0), *LOD_RATIOS.items()):
            target = lod0 if level == 0 else bpy.data.objects.get(lod0.name.replace("_LOD0", f"_LOD{level}"))
            if target is None:
                raise SystemExit(f"missing LOD{level} object for {lod0.name}")
            old = target.data
            target.data = build(source, lod0.matrix_world.copy(), ratio)
            target.data.name = old.name
            if old.users == 0:
                bpy.data.meshes.remove(old)
            if level:
                target.matrix_world = lod0.matrix_world.copy()
                by_level[level].append(target)
        bpy.data.meshes.remove(source)
        report["parts"][lod0.name] = {"before": before, "after": audit(lod0), "welded_vertices": welded}
    for level, objects in by_level.items():
        report["lods"][f"lod{level}"] = {o.name: audit(o) for o in objects}
        report[f"lod{level}_triangles"] = sum(audit(o)["triangles"] for o in objects)
        export(PKG / "unreal" / f"habitat_LOD{level}.fbx", objects)
    bpy.context.scene[MARK] = "v2 weld+decimate+solidify+smooth (2026-11-15)"
    bpy.ops.wm.save_as_mainfile(filepath=str(PKG / "master.blend"))
    (PKG / "fix_report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))


main()
