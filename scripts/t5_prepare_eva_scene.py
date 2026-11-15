"""Technical EV1 gameplay fixture using existing approved art, no generation.

Keeps the user-approved atmosphere in a separate map. Final UI and scene design
are not changed. UE owns the human; all robot authority remains in ROS/Gazebo.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import traceback
import unreal

repo = Path(os.environ["REDLINE_REPO"])
target = "/Game/EVAFixtures"
report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "passed": False,
          "status": "SCENARIO", "map": target + "/BXW_EVA", "source_files": []}
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary


def record(path):
    path = repo / path
    report["source_files"].append({"path": str(path.relative_to(repo)),
                                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return str(path)


def texture(filename, name, normal=False, color=False):
    task = unreal.AssetImportTask()
    task.filename = record("assets/incoming/astronaut/textures/" + filename)
    task.destination_path = target + "/Astronaut"
    task.destination_name = name
    task.automated = task.save = True
    task.replace_existing = True
    tools.import_asset_tasks([task])
    obj = next(o for o in task.get_objects() if isinstance(o, unreal.Texture2D))
    obj.set_editor_property("srgb", color)
    if normal: obj.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    unreal.EditorAssetLibrary.save_loaded_asset(obj)
    return obj


def material(name):
    m = unreal.load_asset(target + "/" + name)
    if not m: m = tools.create_asset(name, target, unreal.Material, unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(m)
    return m


try:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    runtime = json.loads((repo / "data/engines/BXW/eva-runtime-v1.json").read_text())
    record("data/engines/BXW/eva-runtime-v1.json")
    record("assets/incoming/astronaut/SOURCE.md")
    textures = [
        ("Color_7583fea2_05ef_4340_8cc9_5b5a756d3eb4.png", "T_EV1_BaseColor", unreal.MaterialProperty.MP_BASE_COLOR, False, True),
        ("astronaut_NormalDX.png", "T_EV1_Normal", unreal.MaterialProperty.MP_NORMAL, True, False),
        ("astronaut_Roughness.png", "T_EV1_Roughness", unreal.MaterialProperty.MP_ROUGHNESS, False, False),
        ("astronaut_Metallic.png", "T_EV1_Metallic", unreal.MaterialProperty.MP_METALLIC, False, False),
        ("astronaut_AO.png", "T_EV1_AO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, False, False),
    ]
    body_material = material("M_EV1_Original")
    body_material.set_editor_property("used_with_skeletal_mesh", True)
    for filename, name, prop, normal, color in textures:
        tex = texture(filename, name, normal, color)
        sample = lib.create_material_expression(body_material, unreal.MaterialExpressionTextureSample)
        sample.texture = tex
        sample.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if color else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
        if not lib.connect_material_property(sample, "RGB" if normal or color else "R", prop):
            raise RuntimeError("Missing EV1 material input " + str(prop))
    lib.recompile_material(body_material)
    unreal.EditorAssetLibrary.save_loaded_asset(body_material, False)
    task = unreal.AssetImportTask()
    task.filename = record("assets/incoming/astronaut/unreal/astronaut_LOD0.fbx")
    task.destination_path, task.destination_name = target + "/Astronaut", "SK_Astronaut"
    task.automated = task.save = task.replace_existing = True
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_materials = options.import_textures = options.import_animations = False
    options.skeletal_mesh_import_data.convert_scene = True
    options.skeletal_mesh_import_data.convert_scene_unit = True
    options.skeletal_mesh_import_data.force_front_x_axis = False
    task.options = options
    tools.import_asset_tasks([task])
    mesh = next(o for o in task.get_objects() if isinstance(o, unreal.SkeletalMesh))
    skeleton = mesh.get_editor_property("skeleton")
    if not skeleton: raise RuntimeError("Skeletal import has no skeleton")
    # AssetImportTask.save does not persist every generated dependency in this
    # installed editor. Explicitly save the skeleton before its mesh/animations.
    unreal.EditorAssetLibrary.save_loaded_asset(skeleton, False)
    slots = []
    for old_slot in mesh.get_editor_property("materials"):
        # Iterating a reflected UE struct array yields copies. Build a Python
        # list of updated structs rather than changing discarded loop copies.
        slot = unreal.SkeletalMaterial()
        slot.set_editor_property("material_slot_name", old_slot.material_slot_name)
        slot.set_editor_property("material_interface", body_material)
        slots.append(slot)
    mesh.set_editor_property("materials", slots)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
    if any(not slot.material_interface for slot in mesh.materials):
        raise RuntimeError("EV1 material slot is empty after assignment")
    report["skeleton"] = skeleton.get_path_name()
    bounds = mesh.get_bounds().box_extent
    report["dimensions_cm"] = [bounds.x * 2, bounds.y * 2, bounds.z * 2]
    if abs(bounds.z * 2 - 185.0125) > 5: raise RuntimeError("Astronaut FBX height is not metre-scale")
    report["animations"] = []
    for clip in ("Idle", "Walk"):
        anim_task = unreal.AssetImportTask()
        anim_task.filename = record("assets/incoming/astronaut/unreal/AN_Astronaut_" + clip.lower() + ".fbx")
        anim_task.destination_path, anim_task.destination_name = target + "/Astronaut", "AN_" + clip
        anim_task.automated = anim_task.save = anim_task.replace_existing = True
        ui = unreal.FbxImportUI()
        ui.automated_import_should_detect_type = False
        ui.import_mesh = False
        ui.import_animations = True
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
        ui.skeleton = skeleton
        ui.override_animation_name = "AN_" + clip
        ui.anim_sequence_import_data.convert_scene = True
        ui.anim_sequence_import_data.convert_scene_unit = True
        anim_task.options = ui
        tools.import_asset_tasks([anim_task])
        anim = next(o for o in anim_task.get_objects() if isinstance(o, unreal.AnimSequence))
        if anim.get_editor_property("skeleton") != skeleton:
            raise RuntimeError("Animation skeleton does not match EV1: " + clip)
        if not unreal.RedlineEVAImportLibrary.normalize_locomotion_root(mesh, anim):
            raise RuntimeError("Cannot align animation root with the existing mesh bind scale")
        unreal.EditorAssetLibrary.save_loaded_asset(anim, False)
        tracks = unreal.AnimationLibrary.get_animation_track_names(anim)
        if len(tracks) < 50: raise RuntimeError("Animation imported without bone tracks")
        report["animations"].append({"path": anim.get_path_name(), "length_s": anim.get_play_length(), "tracks": len(tracks)})
    unreal.EditorAssetLibrary.save_directory(target + "/Astronaut", False, True)
    field = material("M_FieldTile")
    field.set_editor_property("material_domain", unreal.MaterialDomain.MD_DEFERRED_DECAL)
    field.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    sample = lib.create_material_expression(field, unreal.MaterialExpressionTextureSampleParameter2D)
    sample.set_editor_property("parameter_name", "FieldTile")
    sample.texture = unreal.load_asset("/Engine/EngineResources/DefaultTexture.DefaultTexture")
    position = lib.create_material_expression(field, unreal.MaterialExpressionWorldPosition)
    origin = lib.create_material_expression(field, unreal.MaterialExpressionVectorParameter)
    origin.set_editor_property("parameter_name", "GridOrigin")
    size = lib.create_material_expression(field, unreal.MaterialExpressionVectorParameter)
    size.set_editor_property("parameter_name", "GridSize")
    size.set_editor_property("default_value", unreal.LinearColor(100000,100000,0,1))
    uv = lib.create_material_expression(field, unreal.MaterialExpressionCustom)
    uv.set_editor_property("code", "return float2((P.x-O.x)/S.x,(-P.y-O.y)/S.y);")
    uv.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    inputs = []
    for name in ("P", "O", "S"):
        value = unreal.CustomInput()
        value.set_editor_property("input_name", name)
        inputs.append(value)
    uv.set_editor_property("inputs", inputs)
    for name, node in (("P", position), ("O", origin), ("S", size)):
        lib.connect_material_expressions(node, "", uv, name)
    pins = [str(n) for n in lib.get_material_expression_input_names(sample)]
    coordinate_pin = next((n for n in pins if n in ("UVs", "Coordinates")), None)
    report["field_uv_pin"] = coordinate_pin
    if not coordinate_pin or not lib.connect_material_expressions(uv, "", sample, coordinate_pin):
        raise RuntimeError("World/map tile UV connection failed")
    lib.connect_material_property(sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    lib.connect_material_property(sample, "A", unreal.MaterialProperty.MP_OPACITY)
    lib.recompile_material(field)
    unreal.EditorAssetLibrary.save_loaded_asset(field)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    levels.load_level("/Game/VisualShowcase/BXW_Atmosphere_Autonomy")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for actor in list(actors.get_all_level_actors()):
        if isinstance(actor, unreal.CameraActor): actor.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.DISABLED)
        if isinstance(actor, unreal.PlayerStart): actors.destroy_actor(actor)
    x, y, z = runtime["spawn_map_xyz_m"]
    coords = unreal.load_class(None, "/Script/RedlineBridge.RedlineCoords")
    # Native acceptance trace uses the actual imported terrain, not the 4 m average.
    hit = unreal.RedlineCoords.trace_terrain_height(world, unreal.Vector(x,y,z), 100.)
    if not isinstance(hit, unreal.Vector): raise RuntimeError("No collision terrain at the habitat spawn")
    z = hit.z
    start = actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(x*100,-y*100,z*100+98),
                                         unreal.Rotator(pitch=0,yaw=0,roll=0))
    start.set_actor_label("SCENARIO_EV1_Habitat_Start")
    world.get_world_settings().set_editor_property("default_game_mode", unreal.load_class(None, "/Script/Redline.RedlineEVAGameMode"))
    world.get_world_settings().set_editor_property("global_gravity_z", -runtime["gravity_m_s2"]*100)
    world.get_world_settings().set_editor_property("global_gravity_set", True)
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, report["map"]): raise RuntimeError("EVA map save failed")
    report.update(passed=True, spawn_map_xyz_m=[x,y,z], human_authority="Unreal CharacterMovement",
                  robot_authority="ROS/Gazebo; unchanged", final_ui_design=False)
except Exception as error:
    report.update(error=repr(error), traceback=traceback.format_exc())
finally:
    (repo / "test-results/t5-eva-scene-import.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("REDLINE_EVA_SCENE " + json.dumps(report))
if not report["passed"]: raise RuntimeError(report.get("error", "Scene preparation failed"))
