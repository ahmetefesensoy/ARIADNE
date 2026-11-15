"""Import the approved drill's existing 20 parts without synthesizing a bit.

Existing original PBR material is reused; all parts have source absolute bind
vertices. Animate the real bit through a pivot at pivot_cm and child offset
-pivot_cm. Do not render the full combined drill on top of these parts.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import traceback
import unreal

root = Path(os.environ["REDLINE_REPO"]).resolve()
folder = root / "assets/incoming/tool_drill"
dest = "/Game/MissionProps/tool_drill_parts"
report = {"schema": "redline.drill_parts.v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
          "passed": False, "status": "SCENARIO", "parts": [], "sources": [],
          "limitation": "Existing Tripo visual pieces and authored pivots; no flight CAD, joint limits, torque/force or soil physics. Bit rotation is cosmetic."}


def record(path):
    path = path.resolve()
    report["sources"].append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return path


try:
    metadata = json.loads(record(folder / "asset.json").read_text())
    bindings = json.loads(record(folder / "material_bindings.json").read_text())
    record(folder / "SOURCE.md")
    if not any(p["name"] == "SM_tool_drill_bit_LOD0" for p in metadata["parts"]):
        raise ValueError("No separated source bit; cannot invent geometry")
    receipt = json.loads((Path(unreal.Paths.project_content_dir()) / "MissionProps/mission_props.json").read_text())
    if receipt["assets"]["tool_drill"]["material_bindings"] != bindings:
        raise ValueError("Drill material source changed")
    materials = {s["source_material"]: unreal.load_asset(s["material"])
                 for s in receipt["assets"]["tool_drill"]["source_materials"]}
    if len(materials) != 1 or not all(materials.values()):
        raise ValueError("Original drill PBR material unavailable")
    fbx = record(folder / metadata["exports"]["unreal_lod0"].replace("\\", "/"))
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = options.import_materials = options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = data.auto_generate_collision = False
    data.convert_scene = data.convert_scene_unit = data.transform_vertex_to_absolute = True
    data.force_front_x_axis = data.generate_lightmap_u_vs = False
    task = unreal.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = str(fbx), dest, "SM_DrillPart"
    task.automated = task.replace_existing = True
    task.save = False
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes = [o for o in task.get_objects() if isinstance(o, unreal.StaticMesh)]
    if len(meshes) != len(metadata["parts"]):
        raise ValueError("Source drill part count differs")
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    low, high = [float("inf")]*3, [-float("inf")]*3
    for mesh in meshes:
        matches = [p for p in metadata["parts"] if p["name"] in mesh.get_name()]
        if len(matches) != 1:
            raise ValueError("Unknown source drill part " + mesh.get_name())
        part = matches[0]
        for index in range(len(mesh.get_editor_property("static_materials"))):
            mesh.set_material(index, next(iter(materials.values())))
        subsystem.remove_collisions(mesh)
        for index in range(mesh.get_num_sections(0)):
            subsystem.enable_section_collision(mesh, False, 0, index)
        box = mesh.get_bounding_box()
        for index, axis in enumerate(("x", "y", "z")):
            low[index] = min(low[index], getattr(box.min, axis))
            high[index] = max(high[index], getattr(box.max, axis))
        x, y, z = part["pivot_m"]
        pivot = [100*x, -100*y, 100*z]
        item = {"name": part["name"], "source_name": part["source_name"], "asset": mesh.get_path_name(),
                "mesh_asset": mesh.get_path_name(), "pivot_cm": pivot, "bind_location_cm": [0., 0., 0.],
                "pivot_child_offset_cm": [-v for v in pivot], "bounds_min_cm": [box.min.x, box.min.y, box.min.z],
                "bounds_max_cm": [box.max.x, box.max.y, box.max.z], "collision": False,
                "is_bit": part["name"] == "SM_tool_drill_bit_LOD0"}
        report["parts"].append(item)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
    dimensions = [b-a for a, b in zip(low, high)]
    error = max(abs(a-b*100.) for a, b in zip(dimensions, metadata["master"]["dimensions_m"]))
    if error > .1:
        raise ValueError("Drill parts source dimensions differ")
    bit = next(p for p in report["parts"] if p["is_bit"])
    report.update(passed=True, dimensions_cm=dimensions, unit_error_cm=error, bit_asset=bit["mesh_asset"],
        bit_origin_cm=bit["pivot_cm"], bit_pivot_child_offset_cm=bit["pivot_child_offset_cm"],
        source_notice="assets/incoming/tool_drill/SOURCE.md",
        axis_contract="UE centimetres; absolute bind vertices, no recentering; use pivot and negative child offset for rotation.")
    for item in report["sources"]:
        if hashlib.sha256((root/item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError("Source changed during import")
    content = Path(unreal.Paths.project_content_dir()).resolve() / "MissionProps"
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    (content / "tool_drill_parts.json").write_text(text, encoding="utf-8")
    (content / "tool_drill_parts/parts.json").write_text(text, encoding="utf-8")
    target = root / "unreal/Redline/Content/MissionProps"
    if content != target.resolve():
        shutil.copytree(content/"tool_drill_parts", target/"tool_drill_parts", dirs_exist_ok=True)
        shutil.copy2(content/"tool_drill_parts.json", target/"tool_drill_parts.json")
except Exception as error:
    report["passed"] = False
    report["error"] = str(error)
    report["traceback"] = traceback.format_exc()
    raise
finally:
    (root / "test-results/drill-parts-import.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
