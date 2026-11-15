"""Propagate revised texture files into a delivered package's master.blend and GLB.

Usage: blender --background --factory-startup --python refresh_textures.py
Reads production/texture_fixes.json. For each revised texture the packed image in
master.blend is replaced by the new file, presentation.glb is re-exported from the LOD0
meshes, previews are re-rendered and asset.json/SOURCE.md record the revision. FBX files
already point at the rewritten .fbm copies; OBJ materials at textures/.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from preview import views  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REASONS = {
    "habitat": "NASA insignia, US flags, the HAB X logo and HDU emblems removed (proje kılavuzu §8: no NASA brand "
               "elements; NASA media guidelines restrict insignia use). Generic Segment/AIRLOCK signage kept.",
    "sample_case": "Blue Earth warehouse tote recoloured to the project's light-grey palette; wear and labels kept.",
}


def refresh(aid: str, fix: dict) -> None:
    folder = ROOT / "incoming" / aid
    bpy.ops.wm.open_mainfile(filepath=str(folder / "master.blend"), load_ui=False, use_scripts=False)
    new_path = folder / "textures" / fix["texture"]
    replaced = 0
    for old in [i for i in bpy.data.images if Path(bpy.path.abspath(i.filepath_raw)).name == fix["texture"]]:
        new = bpy.data.images.load(str(new_path), check_existing=False)
        new.colorspace_settings.name = old.colorspace_settings.name
        for mat in bpy.data.materials:
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == "TEX_IMAGE" and node.image == old:
                        node.image = new
                        replaced += 1
        name = old.name
        bpy.data.images.remove(old)
        new.name = name
        new.pack()
    if not replaced:
        raise SystemExit(f"{aid}: no material used {fix['texture']}")
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "master.blend"))
    lod0 = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("SM_") and o.name.endswith("LOD0")]
    bpy.ops.object.select_all(action="DESELECT")
    for o in lod0:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = lod0[0]
    bpy.ops.export_scene.gltf(filepath=str(folder / "presentation.glb"), export_format="GLB", use_selection=True,
                              export_animations=False)
    views(lod0, folder / "preview", ("perspective", "front", "side", "back"), 640)
    meta = folder / "asset.json"
    data = json.loads(meta.read_text(encoding="utf-8"))
    data.setdefault("revisions", []).append({
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "texture": fix["texture"],
        "reason": REASONS[aid], "sha256_before": fix["sha256_before"], "sha256_after": fix["sha256_after"],
        "files": fix["files"] + [f"incoming/{aid}/master.blend (packed image)", f"incoming/{aid}/presentation.glb"],
        "script": "production/texture_fixes.py + production/refresh_textures.py", "material_slots_rebound": replaced})
    meta.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    source = folder / "SOURCE.md"
    text = source.read_text(encoding="utf-8").rstrip("\n")
    source.write_text(text + f"\n\nRevizyon (14 Kasım 2026): {REASONS[aid]} Doku SHA256 `{fix['sha256_before'][:12]}…` → "
                      f"`{fix['sha256_after'][:12]}…`; ayrıntı `asset.json → revisions`.\n", encoding="utf-8")
    print("REFRESHED", aid, replaced, "slots", flush=True)


if __name__ == "__main__":
    fixes = json.loads((ROOT / "production/texture_fixes.json").read_text(encoding="utf-8"))
    for aid in ("habitat", "sample_case"):
        refresh(aid, fixes[aid])
