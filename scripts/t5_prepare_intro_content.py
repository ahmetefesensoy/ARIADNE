"""Place existing habitat/map table/context station in the separate EVA map.

SCENARIO orientation staging only. No source art edits or generated assets;
this is an exterior start, not a claimed walkable habitat interior or T8 science.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import traceback
import unreal

repo = Path(os.environ['REDLINE_REPO'])
dest = '/Game/EVAFixtures/Intro'
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
report = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'SCENARIO',
          'passed': False, 'sources': [], 'placed': [], 'map': '/Game/EVAFixtures/BXW_EVA'}


def record(path):
    path = repo / path
    report['sources'].append({'path': str(path.relative_to(repo)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return str(path)


def task(path, folder, name, options=None):
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.destination_name = record(path), folder, name
    t.automated = t.replace_existing = True
    t.save = False  # save generated dependencies explicitly below
    if options: t.options = options
    tools.import_asset_tasks([t])
    for asset in t.get_objects(): unreal.EditorAssetLibrary.save_loaded_asset(asset, False)
    return t.get_objects()


def bound_material(asset_id, binding_name, channels):
    folder = dest + '/' + asset_id
    name = 'M_' + asset_id + '_' + str(abs(sum(ord(c) for c in binding_name)))
    mat = unreal.load_asset(folder + '/' + name)
    if not mat: mat = tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(mat)
    properties = {'Base Color':unreal.MaterialProperty.MP_BASE_COLOR, 'Roughness':unreal.MaterialProperty.MP_ROUGHNESS,
                  'Metallic':unreal.MaterialProperty.MP_METALLIC, 'Normal':unreal.MaterialProperty.MP_NORMAL}
    for key, binding in channels.items():
        if key not in properties: continue
        if 'path' in binding:
            filename = Path(binding['path'].replace('\\','/'))
            tex = next(o for o in task('assets/incoming/'+asset_id+'/'+str(filename), folder, 'T_'+asset_id+'_'+filename.stem)
                       if isinstance(o,unreal.Texture2D))
            tex.set_editor_property('srgb', key == 'Base Color')
            if key == 'Normal':
                tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
                tex.set_editor_property('flip_green_channel',binding.get('normal_convention') == 'OpenGL')
            unreal.EditorAssetLibrary.save_loaded_asset(tex,False)
            node = lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample)
            node.texture = tex
            node.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if key == 'Normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if key == 'Base Color' else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
            output = binding.get('component','RGB')
        elif isinstance(binding.get('constant'), (int,float)):
            node = lib.create_material_expression(mat,unreal.MaterialExpressionConstant)
            # Existing HDU source labels all painted surfaces metallic; keep
            # source notice but use a nonmetal paint derivative for readability.
            node.r = 0. if asset_id == 'habitat' and key == 'Metallic' else binding['constant']
            output = ''
        else: continue
        if not lib.connect_material_property(node,output,properties[key]): raise RuntimeError('Material pin '+key)
    lib.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
    return mat


try:
    unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    runtime = json.loads((repo/'data/engines/BXW/eva-runtime-v1.json').read_text())
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(report['map'])
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label() == 'SCENARIO_Diffuse_Dust_Bounce_Fill':
            # Existing rover look's bounce pointed away from the EV1 follow
            # camera. Give fabric/face a readable, fixed diffuse sky fill here.
            actor.set_actor_rotation(unreal.Rotator(pitch=-45,yaw=0,roll=0),False)
            actor.light_component.set_intensity(5000.)
    for actor in list(actors.get_all_level_actors()):
        label = actor.get_actor_label()
        if label.startswith('INTRO_') or label.startswith('SCENARIO_moving_') or label.startswith('SCENARIO_showcase_') or label == 'SCENARIO_lidar_acceptance_obstacle':
            actors.destroy_actor(actor)
    x,y = runtime['intro']['briefing_xy_m']
    sx,sy = runtime['intro']['station_xy_m']
    placements = [('habitat',x-7,y+5),('map_table',x-1.8,y+1.8),('science_station',sx,sy)]
    for asset_id,px,py in placements:
        record('assets/incoming/'+asset_id+'/SOURCE.md')
        meta = json.loads((repo/'assets/incoming'/asset_id/'asset.json').read_text())
        ui = unreal.FbxImportUI()
        ui.automated_import_should_detect_type = False
        ui.import_mesh = True
        ui.import_as_skeletal = False
        ui.import_materials = True
        ui.import_textures = False
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        d = ui.static_mesh_import_data
        d.combine_meshes = True
        d.auto_generate_collision = True
        d.convert_scene = d.convert_scene_unit = True
        d.generate_lightmap_u_vs = False
        objects = task('assets/incoming/'+asset_id+'/unreal/'+asset_id+'_LOD0.fbx',dest+'/'+asset_id,'SM_'+asset_id,ui)
        mesh = next(o for o in objects if isinstance(o,unreal.StaticMesh))
        box = mesh.get_bounding_box()
        dimensions = box.max-box.min
        expected = meta['master']['dimensions_m']
        error = max(abs(a-b*100) for a,b in zip((dimensions.x,dimensions.y,dimensions.z),expected))
        if error>1.: raise RuntimeError('Units changed '+asset_id)
        binding_path = repo/'assets/incoming'/asset_id/'material_bindings.json'
        if binding_path.exists():
            bindings = json.loads(binding_path.read_text())
            mats = [bound_material(asset_id,key,channels) for key,channels in bindings.items()]
            for i in range(len(mesh.get_editor_property('static_materials'))): mesh.set_material(i,mats[min(i,len(mats)-1)])
        unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
        ground = unreal.RedlineCoords.trace_terrain_height(world,unreal.Vector(px,py,runtime['spawn_map_xyz_m'][2]),100.)
        if not isinstance(ground,unreal.Vector): raise RuntimeError('No terrain under '+asset_id)
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(px*100,-py*100,ground.z*100-box.min.z+1))
        actor.set_actor_label('INTRO_'+asset_id)
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        actor.static_mesh_component.set_simulate_physics(False)
        report['placed'].append({'id':asset_id,'map_xyz_m':[px,py,ground.z],
            'dimensions_cm':[dimensions.x,dimensions.y,dimensions.z],'unit_error_cm':error})
    if not unreal.EditorLoadingAndSavingUtils.save_map(world,report['map']): raise RuntimeError('Map save failed')
    unreal.EditorAssetLibrary.save_directory(dest,False,True)
    report['passed'] = True
except Exception as e:
    report.update(error=repr(e),traceback=traceback.format_exc())
finally:
    (repo/'test-results/eva-intro-content.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    unreal.log('INTRO_CONTENT '+json.dumps(report))
if not report['passed']: raise RuntimeError(report.get('error','Intro content failed'))
