"""Unreal Editor Python: isolated surface-v2 assets and an EVA map copy.

REDLINE_REPO is required. REDLINE_SURFACE_SOURCE selects the source package
(default data/engines/BXW/surface-v2-1m). Original EVA and T4 maps stay intact.
The existing presentation material is retained; robot physics stays in Gazebo.
"""
from datetime import datetime,timezone
import hashlib,json,os,traceback
from pathlib import Path
import unreal

root=Path(os.environ['REDLINE_REPO']).resolve()
source=root/os.environ.get('REDLINE_SURFACE_SOURCE','data/engines/BXW/surface-v2-1m')
exports=root/'data/engines/BXW/surface-blender-v2-1m'
dest='/Game/DerivedSurfaceV2';map_path='/Game/EVAFixtures/BXW_EVA_SurfaceV2'
report_path=root/'test-results/surface-v2-unreal-import.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report={'schema':'redline.surface.unreal.v2','created_at_utc':datetime.now(timezone.utc).isoformat(),'engine':unreal.SystemLibrary.get_engine_version(),
    'passed':False,'map':map_path,'source_map':'/Game/EVAFixtures/BXW_EVA','status':'DERIVED','meshes':[],'trace_checks':[],
    'authority':'UE terrain query collision for human only; ROS/Gazebo robot physics unchanged','original_map_modified':False}
try:
    manifest_path=source/'manifest.json';manifest=json.loads(manifest_path.read_text());fbx=json.loads((exports/'verification.json').read_text())
    report['source_manifest_sha256']=sha(manifest_path);report['fbx_verification_sha256']=sha(exports/'verification.json')
    if not fbx['passed'] or fbx['source_manifest_sha256']!=report['source_manifest_sha256']:raise ValueError('Unverified source/FBX contract')
    if manifest['frame']!='map' or manifest['units']!='m' or manifest['engine_z_offset_m']!=0:raise ValueError('Unexpected frame/units/datum')
    unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    material=unreal.load_asset('/Game/VisualShowcase/Materials/M_ScenarioSand_context')
    if not material:raise ValueError('Existing context sand material missing; refusing visual fallback')
    report['material']=material.get_path_name();report['texture_source']='surface-v1/atlas_context.png; existing archive-derived 3 km context atlas'
    ui=unreal.FbxImportUI();ui.automated_import_should_detect_type=False;ui.import_mesh=True;ui.import_as_skeletal=False
    ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH;ui.import_materials=ui.import_textures=False
    data=ui.static_mesh_import_data;data.combine_meshes=False;data.auto_generate_collision=False;data.convert_scene=True
    data.convert_scene_unit=True;data.force_front_x_axis=False;data.generate_lightmap_u_vs=False;data.transform_vertex_to_absolute=True
    meshes={}
    for item in fbx['checks']:
        filename=exports/item['fbx']
        if sha(filename)!=item['fbx_sha256']:raise ValueError('FBX hash mismatch '+item['id'])
        path=dest+'/Meshes/'+filename.stem
        mesh=unreal.load_asset(path)
        if mesh is None:
            task=unreal.AssetImportTask();task.filename=str(filename);task.destination_path=dest+'/Meshes';task.destination_name=filename.stem
            task.automated=task.save=True;task.replace_existing=False;task.options=ui
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            mesh=next(obj for obj in task.get_objects() if isinstance(obj,unreal.StaticMesh))
        # The assets live in an isolated versioned folder. Imported geometry is
        # measured against source extents, triangles and the ENU->UE vertex.
        box=mesh.get_bounding_box();size=box.max-box.min;actual=[size.x,size.y,size.z]
        error=max(abs(a-b*100) for a,b in zip(actual,item['dimensions_m']))
        description=mesh.get_static_mesh_description(0);vertex=description.get_vertex_position(unreal.VertexID(0))
        v=item['first_vertex_m'];expected=[100*v[0],-100*v[1],100*v[2]]
        vertex_error=max(abs(a-b) for a,b in zip([vertex.x,vertex.y,vertex.z],expected))
        uv=description.get_vertex_instance_uv(unreal.VertexInstanceID(0),0)
        triangles=mesh.get_num_triangles(0)
        if error>.1 or vertex_error>.1 or triangles!=item['triangles']:raise ValueError('Geometry/units failed '+item['id'])
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        mesh.set_material(0,material);unreal.EditorAssetLibrary.save_loaded_asset(mesh,False);meshes[item['id']]=mesh
        report['meshes'].append({'id':item['id'],'asset':mesh.get_path_name(),'source_fbx_sha256':item['fbx_sha256'],
            'dimensions_cm':actual,'dimension_error_cm':error,'vertex_error_cm':vertex_error,'uv0':[uv.x,uv.y],'triangles':triangles,'pose_map_m':item['actor_pose_map_m'],'passed':True})
        unreal.log('SURFACE_V2_IMPORT '+str(len(meshes))+'/'+str(len(fbx['checks']))+' '+item['id'])
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    # Copy the existing scene composition. Only terrain actors are replaced.
    if not levels.load_level(report['source_map']):raise ValueError('Cannot load current EVA scene')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    removed=[]
    for actor in list(actors.get_all_level_actors()):
        if isinstance(actor,unreal.StaticMeshActor):
            comp=actor.static_mesh_component;mesh=comp.get_editor_property('static_mesh')
            if mesh and mesh.get_path_name().startswith('/Game/T4Fixtures/Terrain/'):
                removed.append(actor.get_actor_label());actors.destroy_actor(actor)
    if len(removed)!=17:raise ValueError('Expected exactly 17 old terrain actors; found '+str(len(removed)))
    for item in fbx['checks']:
        p=item['actor_pose_map_m'];actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(100*p[0],-100*p[1],100*p[2]))
        actor.set_actor_label('DERIVED_BXW_V2_'+item['id']);actor.tags=[unreal.Name('redline_surface_v2')]
        comp=actor.static_mesh_component;comp.set_static_mesh(meshes[item['id']]);comp.set_material(0,material)
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY);comp.set_simulate_physics(False)
    report['replaced_terrain_actors']=removed
    for p in manifest['qa']['three_point_test']:
        point=unreal.Vector(p['map_x_m'],p['map_y_m'],p['dem_bilinear_z_m'])
        hit=unreal.RedlineCoords.trace_terrain_height(world,point,100.)
        err=abs(hit.z-point.z) if isinstance(hit,unreal.Vector) else None
        check={'id':p['id'],'map_xy_m':[point.x,point.y],'dem_z_m':point.z,'trace_z_m':hit.z if hit is not None else None,'error_m':err,'passed':err is not None and err<=.1}
        report['trace_checks'].append(check)
        if not check['passed']:raise ValueError('Real complex collision trace failed '+p['id'])
    report['passed']=len(report['meshes'])==len(manifest['meshes']) and len(report['trace_checks'])==3
    if not report['passed']:raise ValueError('Incomplete surface import')
    if not unreal.EditorLoadingAndSavingUtils.save_map(world,map_path):raise ValueError('Cannot save isolated EVA v2 map')
except Exception as error:
    report.update(passed=False,error=repr(error),traceback=traceback.format_exc())
finally:
    report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,indent=2)+'\n')
    unreal.log('REDLINE_SURFACE_V2 '+json.dumps(report))
if not report['passed']:raise RuntimeError(report.get('error','incomplete import'))
