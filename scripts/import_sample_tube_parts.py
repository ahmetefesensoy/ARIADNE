"""Import the existing separate sample tube and cap for cosmetic cap motion.

No source art is changed. FBX bind transforms are baked into mesh vertices,
so both components bind at identity. A movable cap pivot uses cap_origin_cm
and a child mesh offset of -cap_origin_cm; no new seal/physics model is implied.
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
folder = root / "assets/incoming/sample_tube"
dest = "/Game/MissionProps/sample_tube_parts"
report = {"schema": "redline.sample_tube_parts.v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
          "status": "SCENARIO", "passed": False, "parts": {}, "sources": [],
          "limitation": "Source cap is an existing SCENARIO derivative, not flight sealing CAD. Visual motion only, no grasp/sealing physics."}


def record(path):
    path = path.resolve()
    report["sources"].append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return path


def import_station_parts():
    """Keep all existing authored station parts; pivots are cosmetic only."""
    station = root / "assets/incoming/science_station"
    metadata = json.loads(record(station / "asset.json").read_text())
    station_bindings = json.loads(record(station / "material_bindings.json").read_text())
    record(station / "SOURCE.md")
    receipt = json.loads((Path(unreal.Paths.project_content_dir()) / "MissionProps/mission_props.json").read_text())
    if receipt["assets"]["science_station"]["material_bindings"] != station_bindings:
        raise ValueError("Station material source changed")
    materials = {s["source_material"]: unreal.load_asset(s["material"])
                 for s in receipt["assets"]["science_station"]["source_materials"]}
    if len(materials) != 1 or not all(materials.values()):
        raise ValueError("Station source material not available")
    fbx = record(station / metadata["exports"]["unreal_lod0"].replace("\\", "/"))
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
    task.filename, task.destination_path, task.destination_name = str(fbx), "/Game/MissionProps/science_station_parts", "SM_StationPart"
    task.automated = task.replace_existing = True
    task.save = False
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes = [o for o in task.get_objects() if isinstance(o, unreal.StaticMesh)]
    if len(meshes) != len(metadata["parts"]):
        raise ValueError("Station source part count changed")
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    low, high, parts = [float("inf")]*3, [-float("inf")]*3, []
    for mesh in meshes:
        matches = [p for p in metadata["parts"] if p["name"] in mesh.get_name()]
        if len(matches) != 1:
            raise ValueError("Unknown station part " + mesh.get_name())
        part = matches[0]
        for index in range(len(mesh.get_editor_property("static_materials"))):
            mesh.set_material(index, next(iter(materials.values())))
        subsystem.remove_collisions(mesh)
        for index in range(mesh.get_num_sections(0)):
            subsystem.enable_section_collision(mesh, False, 0, index)
        box = mesh.get_bounding_box()
        for i, axis in enumerate(("x", "y", "z")):
            low[i] = min(low[i], getattr(box.min, axis))
            high[i] = max(high[i], getattr(box.max, axis))
        x, y, z = part["pivot_m"]
        pivot = [100*x, -100*y, 100*z]
        parts.append({"name": part["name"], "source_name": part["source_name"], "asset": mesh.get_path_name(),
            "mesh_asset": mesh.get_path_name(), "pivot_cm": pivot, "bind_location_cm": [0., 0., 0.],
            "pivot_child_offset_cm": [-v for v in pivot], "collision": False})
        unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
    dimensions = [b-a for a, b in zip(low, high)]
    error = max(abs(a-b*100.) for a, b in zip(dimensions, metadata["master"]["dimensions_m"]))
    if error > .1:
        raise ValueError("Station parts source bounds differ")
    result = {"schema": "redline.science_station_parts.v1", "passed": True, "status": "SCENARIO", "parts": parts,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "dimensions_cm": dimensions, "unit_error_cm": error,
        "source_fbx_sha256": hashlib.sha256(fbx.read_bytes()).hexdigest(), "source_notice": "assets/incoming/science_station/SOURCE.md",
        "axis_contract": "UE centimetres; absolute bind vertices retained, no recentering; pivot child offset required for rotation.",
        "limitation": "Source pivots and separated antenna/sensor/legs are visual hints; no hinge travel, contact or deployment physics is validated."}
    content = Path(unreal.Paths.project_content_dir()).resolve() / "MissionProps"
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    (content / "science_station_parts.json").write_text(text, encoding="utf-8")
    (content / "science_station_parts/parts.json").write_text(text, encoding="utf-8")
    target = root / "unreal/Redline/Content/MissionProps"
    if content != target.resolve():
        shutil.copytree(content/"science_station_parts", target/"science_station_parts", dirs_exist_ok=True)
        shutil.copy2(content/"science_station_parts.json", target/"science_station_parts.json")
    (root / "test-results/science-station-parts-import.json").write_text(text, encoding="utf-8")


try:
    meta = json.loads(record(folder / "asset.json").read_text())
    bindings = json.loads(record(folder / "material_bindings.json").read_text())
    record(folder / "SOURCE.md")
    fbx = record(folder / meta["exports"]["unreal_lod0"].replace("\\", "/"))
    source_parts = {p["source_name"]: p for p in meta["parts"]}
    if set(source_parts) != {"tube", "cap"}:
        raise ValueError("Expected existing source tube and cap; cannot synthesize a cap")
    shared_material_path = "/Game/MissionProps/sample_tube/Materials/M_MAT_Scenario_Titanium.M_MAT_Scenario_Titanium"
    material = unreal.load_asset(shared_material_path)
    if not isinstance(material, unreal.Material):
        raise ValueError("Source-preserving sample tube material must be imported first")
    mission_receipt = json.loads((Path(unreal.Paths.project_content_dir()) / "MissionProps/mission_props.json").read_text())
    if mission_receipt["assets"]["sample_tube"]["material_bindings"] != bindings:
        raise ValueError("Shared material source differs from current package")
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    ui = unreal.FbxImportUI()
    ui.automated_import_should_detect_type = False
    ui.import_mesh = True
    ui.import_as_skeletal = ui.import_materials = ui.import_textures = False
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = ui.static_mesh_import_data
    data.combine_meshes = False
    data.auto_generate_collision = False
    data.convert_scene = data.convert_scene_unit = data.transform_vertex_to_absolute = True
    data.force_front_x_axis = data.generate_lightmap_u_vs = False
    task = unreal.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = str(fbx), dest, "SM_SampleTubePart"
    task.automated = task.replace_existing = True
    task.save = False
    task.options = ui
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes = [o for o in task.get_objects() if isinstance(o, unreal.StaticMesh)]
    if len(meshes) != 2:
        raise ValueError("Expected two separate source FBX meshes, got " + str(len(meshes)))
    low, high = [float("inf")] * 3, [-float("inf")] * 3
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for mesh in meshes:
        matches = [key for key, part in source_parts.items() if part["name"] in mesh.get_name()]
        if len(matches) != 1:
            raise ValueError("Imported part name does not identify source pivot: " + mesh.get_name())
        key = matches[0]
        for index in range(len(mesh.get_editor_property("static_materials"))):
            mesh.set_material(index, material)
        subsystem.remove_collisions(mesh)
        for index in range(mesh.get_num_sections(0)):
            subsystem.enable_section_collision(mesh, False, 0, index)
        box = mesh.get_bounding_box()
        for i, axis in enumerate(("x", "y", "z")):
            low[i] = min(low[i], getattr(box.min, axis))
            high[i] = max(high[i], getattr(box.max, axis))
        x, y, z = source_parts[key]["pivot_m"]
        origin = [100*x, -100*y, 100*z]
        report["parts"][key] = {"mesh_asset": mesh.get_path_name(), "source_name": source_parts[key]["name"],
            "origin_cm": origin, "bind_location_cm": [0., 0., 0.], "pivot_child_offset_cm": [-v for v in origin],
            "bounds_min_cm": [box.min.x, box.min.y, box.min.z], "bounds_max_cm": [box.max.x, box.max.y, box.max.z],
            "triangles": mesh.get_num_triangles(0), "collision": False, "material": shared_material_path}
        unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
    dimensions = [b-a for a, b in zip(low, high)]
    error = max(abs(a - b*100.) for a, b in zip(dimensions, meta["master"]["dimensions_m"]))
    if error > .1:
        raise ValueError("Combined parts no longer match source centimetre dimensions: " + str(dimensions))
    cap, body = report["parts"]["cap"], report["parts"]["tube"]
    report.update(body_asset=body["mesh_asset"], cap_asset=cap["mesh_asset"], cap_origin_cm=cap["origin_cm"],
        body_origin_cm=body["origin_cm"], cap_pivot_child_offset_cm=cap["pivot_child_offset_cm"],
        dimensions_cm=dimensions, min_z_cm=low[2], unit_error_cm=error,
        axis_contract="Source master +X forward/+Y left/+Z up, UE centimetres/+Y right. Absolute bind vertices, no recentering.",
        source_notice="assets/incoming/sample_tube/SOURCE.md", passed=True)
    for item in report["sources"]:
        if hashlib.sha256((root/item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError("Source changed during import")
    content = Path(unreal.Paths.project_content_dir()).resolve() / "MissionProps"
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    (content / "sample_tube_parts.json").write_text(text, encoding="utf-8")
    (content / "sample_tube_parts/parts.json").write_text(text, encoding="utf-8")
    target = root / "unreal/Redline/Content/MissionProps"
    if content != target.resolve():
        shutil.copytree(content/"sample_tube_parts", target/"sample_tube_parts", dirs_exist_ok=True)
        shutil.copy2(content/"sample_tube_parts.json", target/"sample_tube_parts.json")
    if os.environ.get("REDLINE_IMPORT_STATION_PARTS") == "1":
        import_station_parts()
except Exception as error:
    report["passed"] = False
    report["error"] = str(error)
    report["traceback"] = traceback.format_exc()
    raise
finally:
    (root / "test-results/sample-tube-parts-import.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
