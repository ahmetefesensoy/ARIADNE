"""Bind already delivered artwork in a separate, presentation-only preview.

Reads source packages without modifying them. The T4 acceptance map/assets are
left intact. This is a DERIVED display of orbital imagery and SCENARIO rover
art, with Gazebo as the sole physics authority. No generated artwork or credit
spending. NASA/JPL-Caltech source notices remain in assets/incoming/rover_1.
Run with REDLINE_REPO set using UnrealEditor-Cmd -ExecutePythonScript.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import unreal

repo = Path(os.environ['REDLINE_REPO']).resolve()
source = repo / 'data/engines/BXW/surface-v1'
rover_source = repo / 'assets/incoming/rover_1'
dest = '/Game/DerivedPreview'
report_path = repo / 'test-results/t4-live-preview-import.json'
report = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
          'status': 'DERIVED', 'map': dest + '/BXW_LivePreview',
          'source_art_status': 'SCENARIO', 'passed': False,
          'scope': 'existing delivered assets; separate preview, not T4 acceptance',
          'source_files': [], 'terrain': [], 'rover': {},
          'physics_authority': 'ROS/Gazebo only', 'final_visual_design': False}


def record(path):
    report['source_files'].append({'path': str(path.relative_to(repo)),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})


def import_file(path, folder, name=None, options=None):
    record(path)
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = folder
    if name:
        task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options:
        task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return task.get_objects()


def material(name, binding):
    path = dest + '/Materials/' + name
    mat = unreal.load_asset(path)
    if mat:
        return mat
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, dest + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary
    color = binding['Base Color']
    if 'texture' in color:
        node = lib.create_material_expression(mat, unreal.MaterialExpressionTextureSample)
        node.texture = color['texture']
        lib.connect_material_property(node, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    else:
        node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector)
        v = color['constant']
        node.constant = unreal.LinearColor(v[0], v[1], v[2], 1)
        lib.connect_material_property(node, '', unreal.MaterialProperty.MP_BASE_COLOR)
    for key, prop in [('Roughness', unreal.MaterialProperty.MP_ROUGHNESS),
                      ('Metallic', unreal.MaterialProperty.MP_METALLIC)]:
        node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant)
        node.r = binding[key]['constant']
        lib.connect_material_property(node, '', prop)
    lib.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


try:
    unreal.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
    manifest_path = source / 'manifest.json'
    record(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    exports = json.loads((repo / 'data/engines/BXW/surface-blender-v1/verification.json').read_text(encoding='utf-8'))
    asset = json.loads((rover_source / 'asset.json').read_text(encoding='utf-8'))
    for path in [rover_source / 'asset.json', rover_source / 'SOURCE.md',
                 rover_source / 'material_bindings.json', source / 'imagery.json']:
        record(path)
    terrain_materials = {}
    for kind in ['ops', 'context']:
        png = source / ('atlas_' + kind + '.png')
        recorded = next(a for a in manifest['artifacts'] if a['relative_path'] == png.name)
        if hashlib.sha256(png.read_bytes()).hexdigest() != recorded['sha256']:
            raise RuntimeError('Terrain texture does not match manifest: ' + png.name)
        tex = next(o for o in import_file(png, dest + '/Textures') if isinstance(o, unreal.Texture2D))
        tex.set_editor_property('srgb', True)
        unreal.EditorAssetLibrary.save_loaded_asset(tex)
        terrain_materials[kind] = material('M_BXW_Archive_' + kind, {
            'Base Color': {'texture': tex}, 'Roughness': {'constant': .9}, 'Metallic': {'constant': 0}})
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world.get_world_settings().set_editor_property('force_no_precomputed_lighting', True)
    for item in exports['checks']:
        mesh_path = '/Game/T4Fixtures/Terrain/' + Path(item['fbx'].replace('\\', '/')).stem
        mesh = unreal.load_asset(mesh_path)
        if not mesh:
            raise RuntimeError('Missing previously verified terrain mesh: ' + mesh_path)
        p = item['actor_pose_map_m']
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(p[0]*100, -p[1]*100, p[2]*100))
        actor.set_actor_label('DERIVED_BXW_' + item['id'])
        comp = actor.static_mesh_component
        comp.set_static_mesh(mesh)
        comp.set_material(0, terrain_materials['context' if item['id'] == 'coarse_ring' else 'ops'])
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        comp.set_simulate_physics(False)
        report['terrain'].append({'id': item['id'], 'mesh': mesh_path,
            'material_override': comp.get_material(0).get_path_name(), 'source_asset_modified': False})
    # The delivered FBX carries the original object locations; combine preserves
    # its metre-scale master assembly. The art origin is shifted to the same
    # middle-axle/chassis-height base_link used by stage_delivered_rover.py.
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials = False
    options.import_textures = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.import_uniform_scale = 1
    data.convert_scene = True
    data.convert_scene_unit = True
    data.force_front_x_axis = False
    data.transform_vertex_to_absolute = True
    data.generate_lightmap_u_vs = False
    mesh = next(o for o in import_file(rover_source / 'unreal/rover_1_LOD0.fbx',
        dest + '/Rover', 'SM_DeliveredRover', options) if isinstance(o, unreal.StaticMesh))
    box = mesh.get_bounding_box()
    delta = box.max - box.min
    dims = [delta.x, delta.y, delta.z]
    expected = [v*100 for v in asset['master']['dimensions_m']]
    if max(abs(a-b) for a,b in zip(dims, expected)) > .1:
        raise RuntimeError('Delivered rover dimensions/axes differ: ' + str(dims))
    bindings = json.loads((rover_source / 'material_bindings.json').read_text(encoding='utf-8'))
    materials = {}
    for name, binding in bindings.items():
        if 'path' in binding['Base Color']:
            png = rover_source / binding['Base Color']['path']
            tex = next(o for o in import_file(png, dest + '/Textures') if isinstance(o, unreal.Texture2D))
            tex.set_editor_property('srgb', True)
            unreal.EditorAssetLibrary.save_loaded_asset(tex)
            binding['Base Color'] = {'texture': tex}
        materials[name] = material(name, binding)
    slots = []
    for i, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = str(slot.material_slot_name)
        name = next((n for n in materials if n in name), name)
        if name not in materials:
            raise RuntimeError('Unmapped delivered material slot: ' + name)
        mesh.set_material(i, materials[name])
        slots.append(name)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    spawn = manifest['spawn']
    parts = {p['source_name']:p for p in asset['parts']}
    root = list(parts['Chassis']['pivot_m'])
    root[:2] = [sum(parts[n]['pivot_m'][i] for n in ['wheel_02_L','wheel_02_R'])/2 for i in [0,1]]
    loc = unreal.Vector(spawn['map_x_m']*100, -spawn['map_y_m']*100, (spawn['ground_z_m'] + root[2])*100)
    rot = unreal.Rotator(pitch=0, yaw=-spawn['yaw_rad']*180/3.141592653589793, roll=0)
    rover_class = unreal.load_class(None, '/Script/RedlineBridge.RedlineRoverActor')
    rover = actors.spawn_actor_from_class(rover_class, loc, rot)
    rover.set_actor_label('ROS_Gazebo_Authority_Rover')
    rover.presentation_mesh.set_static_mesh(None)
    visual = actors.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
    visual.set_actor_label('SCENARIO_Delivered_NASA_Rover_Visual')
    visual.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    visual.static_mesh_component.set_static_mesh(mesh)
    visual.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    visual.static_mesh_component.set_simulate_physics(False)
    visual.attach_to_actor(rover, '', unreal.AttachmentRule.KEEP_RELATIVE,
        unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, False)
    visual.set_actor_relative_transform(unreal.Transform(
        location=unreal.Vector(-root[0]*100, root[1]*100, -root[2]*100)), False, False)
    camera = actors.spawn_actor_from_class(unreal.CameraActor, loc, rot)
    camera.set_actor_label('Live_ROS_Rover_Follow_Camera')
    camera.attach_to_actor(rover, '', unreal.AttachmentRule.KEEP_RELATIVE,
        unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, False)
    camera.set_actor_relative_transform(unreal.Transform(location=unreal.Vector(-1000, -700, 650),
        rotation=unreal.Rotator(pitch=-24, yaw=35, roll=0)), False, False)
    camera.camera_component.set_field_of_view(65)
    camera.set_editor_property('auto_activate_for_player', unreal.AutoReceiveInput.PLAYER0)
    sun = actors.spawn_actor_from_class(unreal.DirectionalLight, loc,
        unreal.Rotator(pitch=-40, yaw=-30, roll=0))
    sun.set_actor_label('Preview_Engine_Dynamic_Directional_Light')
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(5)
    sky_class = unreal.load_class(None, '/Engine/EngineSky/BP_Sky_Sphere.BP_Sky_Sphere_C')
    sky = actors.spawn_actor_from_class(sky_class, loc)
    sky.set_actor_label('Preview_Existing_Engine_Sky')
    ambient = actors.spawn_actor_from_class(unreal.SkyLight, loc)
    ambient.set_actor_label('Preview_Engine_Dynamic_Sky_Light')
    ambient.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    ambient.light_component.set_intensity(1)
    ambient.light_component.recapture_sky()
    report['rover'] = {'mesh': mesh.get_path_name(), 'triangles': mesh.get_num_triangles(0),
        'dimensions_cm': dims, 'expected_dimensions_cm': expected, 'material_slots': slots,
        'base_link_origin_in_master_m': root, 'visual_relative_location_cm': [-root[0]*100, root[1]*100, -root[2]*100],
        'collision': 'none', 'physics': False, 'motion': 'parent native actor subscribes ROS odometry',
        'joint_animation': 'not implemented; rigid visual assembly only'}
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, report['map']):
        raise RuntimeError('Could not save derived preview map')
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    editor.set_level_viewport_camera_info(camera.get_actor_location(), camera.get_actor_rotation())
    unreal.SystemLibrary.execute_console_command(world, 'viewmode lit')
    # The combined delivered FBX uses three slots. The fourth binding (parts AO)
    # belongs to a source-library material not used by the delivered assembly.
    expected_slots = {'MAT_NASA_Curiosity_Atlas', 'MAT_NASA_solid', 'MAT_NASA_gold'}
    report['rover']['expected_used_material_slots'] = sorted(expected_slots)
    report['rover']['unused_source_bindings'] = sorted(set(bindings) - set(slots))
    report['passed'] = len(report['terrain']) == 17 and set(slots) == expected_slots
except Exception as error:
    report['error'] = repr(error)
finally:
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    unreal.log('REDLINE_LIVE_PREVIEW ' + json.dumps(report))
if not report['passed']:
    raise RuntimeError(report.get('error', 'Incomplete import'))
