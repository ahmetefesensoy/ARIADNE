"""Existing-asset visual preview: full-res imagery, SCENARIO sand and live wheels.

NASA-derived DEM/UV and base colours remain unchanged. Procedural grain,
ripples, 2 cm wheel depression and tread decals are SCENARIO display effects,
not measured Martian soil or deformable-terrain physics. Sources stay read-only.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
import traceback
from pathlib import Path
import unreal

repo = Path(os.environ['REDLINE_REPO'])
dest = '/Game/VisualShowcase'
lib = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
report = {'observed_at_utc':datetime.now(timezone.utc).isoformat(), 'passed':False,
    'map':dest+'/BXW_Sand_Autonomy', 'status':'SCENARIO', 'source_files':[],
    'limits':['Procedural sand grain/ripples, tyre marks and 2 cm depression are visual SCENARIO effects.',
              'No granular soil physics or flight rocker-bogie model; original DEM/collision remains untouched.']}


def custom(mat, code, kind, sources):
    node = lib.create_material_expression(mat, unreal.MaterialExpressionCustom)
    node.set_editor_property('code', code)
    node.set_editor_property('output_type', kind)
    inputs=[]
    for name in sources:
        value=unreal.CustomInput()
        value.set_editor_property('input_name',name)
        inputs.append(value)
    node.set_editor_property('inputs', inputs)
    for name, (source, output) in sources.items():
        lib.connect_material_expressions(source, output, node, name)
    return node


def constant(mat, number):
    node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant)
    node.r = number
    return node


def new_material(name):
    path = dest+'/Materials/'+name
    mat = unreal.load_asset(path)
    if mat:
        lib.delete_all_material_expressions(mat)
        return mat
    return tools.create_asset(name, dest+'/Materials', unreal.Material, unreal.MaterialFactoryNew())


def import_part(item):
    path = repo/'data/engines/rover-live-parts-v1'/item['file']
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item['sha256']:
        raise RuntimeError('Wheel/body source changed')
    report['source_files'].append({'path':str(path.relative_to(repo)), 'sha256':digest})
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = dest+'/Rover'
    task.destination_name = 'SM_'+item['part']
    task.automated = True
    task.save = True
    task.replace_existing = True
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.convert_scene = True
    data.convert_scene_unit = True
    data.force_front_x_axis = False
    data.transform_vertex_to_absolute = True
    data.generate_lightmap_u_vs = False
    task.options = options
    tools.import_asset_tasks([task])
    mesh = next(obj for obj in task.get_objects() if isinstance(obj, unreal.StaticMesh))
    box = mesh.get_bounding_box()
    size = box.max-box.min
    error = max(abs(a-b*100) for a,b in zip([size.x,size.y,size.z],item['dimensions_m']))
    if error > .1:
        raise RuntimeError('Part units/axes changed '+item['part'])
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = str(slot.material_slot_name)
        name = next((value for value in ['MAT_NASA_Curiosity_Atlas','MAT_NASA_solid','MAT_NASA_gold','MAT_NASA_parts_AO'] if value in name),name)
        material = unreal.load_asset('/Game/DerivedPreview/Materials/'+name)
        if not material:
            raise RuntimeError('Missing original part material '+name)
        mesh.set_material(index, material)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    report.setdefault('imported_parts',[]).append({'part':item['part'], 'dimensions_cm':[size.x,size.y,size.z],
        'triangles':mesh.get_num_triangles(0), 'unit_error_cm':error})
    return mesh


try:
    unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    levels.load_level('/Game/DerivedPreview/BXW_Autonomy_Showcase')
    world = editor.get_editor_world()
    world.get_world_settings().set_editor_property('force_no_precomputed_lighting',True)
    collection = unreal.load_asset(dest+'/MPC_WheelContacts')
    if not collection:
        collection = tools.create_asset('MPC_WheelContacts',dest,unreal.MaterialParameterCollection,
                                       unreal.MaterialParameterCollectionFactoryNew())
    parameters = []
    for i in range(6):
        parameter = unreal.CollectionVectorParameter()
        parameter.set_editor_property('parameter_name','Wheel'+str(i))
        parameter.set_editor_property('default_value',unreal.LinearColor(0,0,0,0))
        parameters.append(parameter)
    collection.set_editor_property('vector_parameters',parameters)
    unreal.EditorAssetLibrary.save_loaded_asset(collection)
    terrain_materials = {}
    report['textures'] = []
    for kind in ('ops','context'):
        texture = unreal.load_asset('/Game/DerivedPreview/Textures/atlas_'+kind)
        texture.set_editor_property('never_stream',True)
        texture.set_editor_property('lod_bias',0)
        texture.set_editor_property('max_texture_size',4096)
        texture.set_editor_property('lod_group',unreal.TextureGroup.TEXTUREGROUP_CINEMATIC)
        unreal.EditorAssetLibrary.save_loaded_asset(texture)
        report['textures'].append({'path':texture.get_path_name(),'width':texture.blueprint_get_size_x(),
                                  'height':texture.blueprint_get_size_y(),'never_stream':True,'lod_bias':0})
        mat = new_material('M_ScenarioSand_'+kind)
        mat.set_editor_property('tangent_space_normal',False)
        sample = lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample)
        sample.texture = texture
        position = lib.create_material_expression(mat,unreal.MaterialExpressionWorldPosition)
        camera_position = lib.create_material_expression(mat,unreal.MaterialExpressionCameraPositionWS)
        normal = lib.create_material_expression(mat,unreal.MaterialExpressionVertexNormalWS)
        grain = custom(mat, '''
float2 q=P.xy; float r=sin(q.x*.41+sin(q.y*.09)*2.1)*.5+.5;
float n=frac(sin(dot(floor(q*2.5),float2(12.9898,78.233)))*43758.5453);
float fade=saturate(1-length(P-Cam)/2200);
float g=lerp(1,lerp(.94,1.035,n)*lerp(.98,1.01,r),fade);
return C*g;
''',unreal.CustomMaterialOutputType.CMOT_FLOAT3,{'P':(position,''),'C':(sample,'RGB'),'Cam':(camera_position,'')})
        lib.connect_material_property(grain,'',unreal.MaterialProperty.MP_BASE_COLOR)
        bump = custom(mat, '''
float2 p=P.xy; float phase=p.x*.41+sin(p.y*.09)*2.1;
float2 slope=float2(.04*cos(phase),.012*cos(phase)*cos(p.y*.09));
float2 grain=float2(sin(p.x*13.7+p.y*3.1),cos(p.y*11.3-p.x*4.7))*.04;
float fade=saturate(1-length(P-Cam)/2200);
return normalize(N-float3((slope+grain)*fade,0));
''',unreal.CustomMaterialOutputType.CMOT_FLOAT3,{'P':(position,''),'N':(normal,''),'Cam':(camera_position,'')})
        lib.connect_material_property(bump,'',unreal.MaterialProperty.MP_NORMAL)
        lib.connect_material_property(constant(mat,.92),'',unreal.MaterialProperty.MP_ROUGHNESS)
        lib.connect_material_property(constant(mat,.18),'',unreal.MaterialProperty.MP_SPECULAR)
        sources = {'P':(position,'')}
        for i in range(6):
            param = lib.create_material_expression(mat,unreal.MaterialExpressionCollectionParameter)
            param.set_editor_property('collection',collection)
            param.set_editor_property('parameter_name','Wheel'+str(i))
            sources['W'+str(i)] = (param,'')
        depression = custom(mat, '''
float d=0; float3 ws[6]={W0.xyz,W1.xyz,W2.xyz,W3.xyz,W4.xyz,W5.xyz};
[unroll] for(int i=0;i<6;i++){float r=length(P.xy-ws[i].xy);d=max(d,saturate(1-r/31));}
return float3(0,0,-2*d*d);
''',unreal.CustomMaterialOutputType.CMOT_FLOAT3,sources)
        lib.connect_material_property(depression,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        lib.recompile_material(mat)
        unreal.EditorAssetLibrary.save_loaded_asset(mat)
        terrain_materials[kind] = mat
    track = new_material('M_ScenarioTyreTread')
    track.set_editor_property('material_domain',unreal.MaterialDomain.MD_DEFERRED_DECAL)
    track.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    uv = lib.create_material_expression(track,unreal.MaterialExpressionTextureCoordinate)
    mask = custom(track, '''
float2 p=UV.xy*2-1;float edge=saturate((1-abs(p.x))*6)*saturate((1-abs(p.y))*6);
float tread=step(.47,frac((p.x+p.y*.22)*5));return edge*lerp(.18,.62,tread);
''',unreal.CustomMaterialOutputType.CMOT_FLOAT1,{'UV':(uv,'')})
    color = lib.create_material_expression(track,unreal.MaterialExpressionConstant3Vector)
    color.constant = unreal.LinearColor(.11,.055,.023,1)
    lib.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
    lib.connect_material_property(mask,'',unreal.MaterialProperty.MP_OPACITY)
    lib.connect_material_property(constant(track,.99),'',unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(track)
    unreal.EditorAssetLibrary.save_loaded_asset(track)
    rover = next(actor for actor in actors.get_all_level_actors() if actor.get_class().get_name()=='RedlineRoverActor')
    old = next(actor for actor in actors.get_all_level_actors() if actor.get_actor_label()=='SCENARIO_Delivered_NASA_Rover_Visual')
    actors.destroy_actor(old)
    rover.set_editor_property('track_decal_material',track)
    rover.set_editor_property('sand_wheel_collection',collection)
    split = json.loads((repo/'data/engines/rover-live-parts-v1/verification.json').read_text())
    if not split['passed']:
        raise RuntimeError('Source split roundtrip is not accepted')
    mapping = {'wheel_01_L':'wheel_fl_link','wheel_02_L':'wheel_ml_link','wheel_03_L':'wheel_rl_link',
               'wheel_01_R':'wheel_fr_link','wheel_02_R':'wheel_mr_link','wheel_03_R':'wheel_rr_link'}
    root = [-.39961522817611694,0,.8886541724205017]
    for item in split['exports']:
        mesh = import_part(item)
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,rover.get_actor_location(),rover.get_actor_rotation())
        actor.set_actor_label('LIVE_'+item['part'])
        comp = actor.static_mesh_component
        comp.set_static_mesh(mesh)
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        comp.set_simulate_physics(False)
        actor.attach_to_actor(rover,'',unreal.AttachmentRule.KEEP_RELATIVE,
                              unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,False)
        pivot = item['pivot_in_master_m']
        xyz = [-root[0]*100,root[1]*100,-root[2]*100] if item['part']=='body' else [
            (pivot[0]-root[0])*100,-(pivot[1]-root[1])*100,(pivot[2]-root[2])*100]
        actor.set_actor_relative_transform(unreal.Transform(location=unreal.Vector(*xyz)),False,False)
        if item['part'] in mapping:
            actor.set_editor_property('tags',[unreal.Name(mapping[item['part']])])
    for actor in actors.get_all_level_actors():
        label = actor.get_actor_label()
        if label.startswith('DERIVED_BXW_'):
            actor.static_mesh_component.set_material(0,terrain_materials['context' if label.endswith('coarse_ring') else 'ops'])
        if isinstance(actor,unreal.DirectionalLight):
            actor.light_component.set_editor_property('contact_shadow_length',.12)
    cube = unreal.load_asset('/Engine/BasicShapes/Cube.Cube')
    for name,x,y,z in [('SCENARIO_moving_crossing_1',143.,-304.,-3597.),
                       ('SCENARIO_moving_crossing_2',151.,-316.,-3597.)]:
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x*100,-y*100,z*100))
        actor.set_actor_label(name)
        actor.set_editor_property('tags',[unreal.Name(name)])
        actor.static_mesh_component.set_static_mesh(cube)
        actor.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        actor.set_actor_scale3d(unreal.Vector(1.2,1.2,3.5))
    camera = next(actor for actor in actors.get_all_level_actors() if actor.get_actor_label()=='Live_ROS_Rover_Follow_Camera')
    camera.set_actor_relative_transform(unreal.Transform(location=unreal.Vector(-700,-500,370),
        rotation=unreal.Rotator(pitch=-18,yaw=35,roll=0)),False,False)
    camera.camera_component.set_field_of_view(62)
    if not unreal.EditorLoadingAndSavingUtils.save_map(world,report['map']):
        raise RuntimeError('Cannot save visual preview')
    report['passed'] = len(report['imported_parts'])==7
except Exception as error:
    report['error'] = repr(error)
    report['traceback'] = traceback.format_exc()
finally:
    (repo/'test-results/t4-visual-showcase-import.json').write_text(json.dumps(report,indent=2)+'\n')
    unreal.log('REDLINE_VISUAL_SHOWCASE '+json.dumps(report))
if not report['passed']:
    raise RuntimeError(report.get('error','Visual preview not complete'))
