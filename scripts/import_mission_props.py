"""Import approved science FBX props without changing maps, source art or scale.

Run with UE Editor Python and REDLINE_REPO set. PBR maps/factors are copied
from material_bindings.json or the existing presentation.glb. No model service
is called. Meshes are presentation-only: no generated or section collision.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import traceback

import unreal

root = Path(os.environ["REDLINE_REPO"]).resolve()
dest = "/Game/MissionProps"
asset_ids = ("station_marker", "sample_tube", "sample_case", "tool_apxs",
             "tool_libs", "tool_neutron", "tool_drill", "lab_bench", "science_station")
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
report = {"schema": "redline.mission_props.import.v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
          "status": "SCENARIO", "passed": False, "assets": {}, "sources": [],
          "limits": "Existing visual art; no measured hardware, mechanical rig, ROS control or physical contact acceptance. SOURCE.md notices preserved."}
source_paths = set()
texture_cache = {}


def source(path):
    path = path.resolve()
    if not path.is_relative_to(root):
        raise ValueError("Source outside repository")
    relative = path.relative_to(root).as_posix()
    if relative not in source_paths:
        report["sources"].append({"path": relative, "bytes": path.stat().st_size,
                                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        source_paths.add(relative)
    return path


def import_file(path, folder, name, options=None):
    task = unreal.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = str(source(path)), folder, name
    task.automated = task.replace_existing = True
    task.save = False
    if options:
        task.options = options
    tools.import_asset_tasks([task])
    return list(task.get_objects())


def glb_materials(path):
    data = source(path).read_bytes()
    if data[:4] != b"glTF" or struct.unpack_from("<I", data, 4)[0] != 2:
        raise ValueError("Expected original glTF 2 material record")
    length, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A:
        raise ValueError("GLB JSON chunk missing")
    return {m["name"]: m for m in json.loads(data[20:20+length])["materials"]}


def bindings_for(folder):
    path = folder / "material_bindings.json"
    originals = glb_materials(folder / "presentation.glb")
    if path.is_file():
        return json.loads(source(path).read_text()), originals, "material_bindings.json"
    # Procedural props have no bindings sidecar. Read exact authored PBR
    # factors from their own GLB; glTF absent metallicFactor means 1.0.
    bindings = {}
    for name, material in originals.items():
        pbr = material.get("pbrMetallicRoughness", {})
        if any(k.endswith("Texture") for k in pbr):
            raise ValueError("GLB texture requires an explicit binding: " + name)
        bindings[name] = {"Base Color": {"constant": pbr.get("baseColorFactor", [1., 1., 1., 1.])},
                          "Roughness": {"constant": pbr.get("roughnessFactor", 1.)},
                          "Metallic": {"constant": pbr.get("metallicFactor", 1.)}}
    return bindings, originals, "presentation.glb PBR factors"


def material_for(asset_id, folder, name, channels, original):
    material_name = "M_" + re.sub(r"[^A-Za-z0-9_]", "_", name)
    location = dest + "/" + asset_id
    mat = unreal.load_asset(location + "/Materials/" + material_name)
    if not mat:
        mat = tools.create_asset(material_name, location + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property("two_sided", original.get("doubleSided", False))
    properties = {"Base Color": unreal.MaterialProperty.MP_BASE_COLOR,
                  "Roughness": unreal.MaterialProperty.MP_ROUGHNESS,
                  "Metallic": unreal.MaterialProperty.MP_METALLIC,
                  "Normal": unreal.MaterialProperty.MP_NORMAL,
                  "Occlusion": unreal.MaterialProperty.MP_AMBIENT_OCCLUSION}
    for channel, entry in channels.items():
        if channel not in properties:
            continue
        if "path" in entry:
            path = (folder / entry["path"].replace("\\", "/")).resolve()
            if not path.is_relative_to(folder):
                raise ValueError("Texture outside source package")
            key = (str(path), channel == "Base Color", channel == "Normal")
            if key not in texture_cache:
                tex = next(o for o in import_file(path, location + "/Textures", "T_" + path.stem)
                           if isinstance(o, unreal.Texture2D))
                tex.set_editor_property("srgb", channel == "Base Color")
                if channel == "Normal":
                    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
                    tex.set_editor_property("flip_green_channel", entry.get("normal_convention") == "OpenGL")
                else:
                    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
                unreal.EditorAssetLibrary.save_loaded_asset(tex, False)
                texture_cache[key] = tex
            node = lib.create_material_expression(mat, unreal.MaterialExpressionTextureSample)
            node.texture = texture_cache[key]
            node.sampler_type = (unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel == "Normal" else
                                 unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if channel == "Base Color" else
                                 unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            output = entry.get("component", "RGB")
        elif isinstance(entry.get("constant"), (int, float)):
            node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant)
            node.r = float(entry["constant"])
            output = ""
        elif channel == "Base Color" and isinstance(entry.get("constant"), list):
            color = entry["constant"]
            node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector)
            node.constant = unreal.LinearColor(*color[:3], 1.)
            output = ""
        elif channel == "Normal" and entry.get("constant") == [0., 0., 0.]:
            # Unlinked Blender normal socket means the surface normal; it is
            # not a literal black tangent-space normal map.
            continue
        else:
            raise ValueError("Unsupported source material channel " + name + "/" + channel)
        if not lib.connect_material_property(node, output, properties[channel]):
            raise RuntimeError("Material connection failed " + name + "/" + channel)
    color = original.get("pbrMetallicRoughness", {}).get("baseColorFactor", [1., 1., 1., 1.])
    if original.get("alphaMode") == "BLEND":
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        opacity = lib.create_material_expression(mat, unreal.MaterialExpressionConstant)
        opacity.r = float(color[3])
        lib.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
    lib.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat, False)
    return mat


try:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for asset_id in asset_ids:
        folder = root / "assets/incoming" / asset_id
        meta = json.loads(source(folder / "asset.json").read_text())
        notice = source(folder / "SOURCE.md")
        if meta["master"]["unit"] != "metre" or meta["master"]["axes"] != "+X forward/+Y left/+Z up":
            raise ValueError("Unsupported package units/axes " + asset_id)
        bindings, originals, material_source = bindings_for(folder)
        fbx = folder / meta["exports"]["unreal_lod0"].replace("\\", "/")
        ui = unreal.FbxImportUI()
        ui.automated_import_should_detect_type = False
        ui.import_mesh = True
        ui.import_as_skeletal = ui.import_materials = ui.import_textures = False
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        data = ui.static_mesh_import_data
        data.combine_meshes = True
        data.auto_generate_collision = False
        data.convert_scene = data.convert_scene_unit = data.transform_vertex_to_absolute = True
        data.force_front_x_axis = data.generate_lightmap_u_vs = False
        mesh = next(o for o in import_file(fbx, dest + "/" + asset_id, "SM_" + asset_id, ui)
                    if isinstance(o, unreal.StaticMesh))
        materials = {name: material_for(asset_id, folder, name, channels, originals.get(name, {}))
                     for name, channels in bindings.items()}
        slots = []
        for index, slot in enumerate(mesh.get_editor_property("static_materials")):
            slot_name = str(slot.material_slot_name)
            matches = [name for name in materials if re.sub(r"[^A-Za-z0-9_]", "_", name) in re.sub(r"[^A-Za-z0-9_]", "_", slot_name)]
            if not matches and len(materials) == 1:
                matches = list(materials)
            if len(matches) != 1:
                raise ValueError("Source material slot not resolved " + asset_id + "/" + slot_name)
            mesh.set_material(index, materials[matches[0]])
            slots.append({"slot": slot_name, "source_material": matches[0], "material": materials[matches[0]].get_path_name()})
        meshes.remove_collisions(mesh)
        for index in range(mesh.get_num_sections(0)):
            meshes.enable_section_collision(mesh, False, 0, index)
        box = mesh.get_bounding_box()
        size = box.max - box.min
        dimensions = [size.x, size.y, size.z]
        error = max(abs(a - b * 100.) for a, b in zip(dimensions, meta["master"]["dimensions_m"]))
        if error > .1:
            raise ValueError("Engine dimensions differ " + asset_id + ": " + str(dimensions))
        unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
        report["assets"][asset_id] = {"mesh_asset": mesh.get_path_name(), "dimensions_cm": dimensions,
            "min_cm": [box.min.x, box.min.y, box.min.z], "max_cm": [box.max.x, box.max.y, box.max.z], "minzcm": box.min.z, "min_z_cm": box.min.z,
            "unit_error_cm": error, "triangles": mesh.get_num_triangles(0), "source_materials": slots,
            "source_fbx_sha256": hashlib.sha256(fbx.read_bytes()).hexdigest(),
            "source_notice": notice.relative_to(root).as_posix(), "material_source": material_source,
            "material_bindings": bindings, "source_parts": meta["parts"],
            "pivot": "Combined source absolute transforms retained; source master origin, centimetres. No recentering.",
            "collision": "none: no generated simple collision, all render sections disabled", "physics": False,
            "status": meta["provenance"]["status"]}
    report["passed"] = True
    content = Path(unreal.Paths.project_content_dir()).resolve() / "MissionProps"
    content.mkdir(parents=True, exist_ok=True)
    (content / "mission_props.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    target = root / "unreal/Redline/Content/MissionProps"
    if content != target.resolve():
        shutil.copytree(content, target, dirs_exist_ok=True)
except Exception as error:
    report["error"] = str(error)
    report["traceback"] = traceback.format_exc()
    raise
finally:
    (root / "test-results/mission-props-import.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
