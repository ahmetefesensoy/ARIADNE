"""Import the existing derived BXW surface and create a T4 acceptance fixture.

No generated models, textures, custom materials or final level design. Reads
REDLINE_REPO from the environment and writes a reproducible technical test map.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import unreal

repo = Path(os.environ['REDLINE_REPO']).resolve()
surface = repo / 'data/engines/BXW/surface-blender-v1'
manifest_path = repo / 'data/engines/BXW/surface-v1/manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
exports = json.loads((surface/'verification.json').read_text(encoding='utf-8'))
report = {'created_at_utc':datetime.now(timezone.utc).isoformat(),
          'status':'DERIVED','engine':unreal.SystemLibrary.get_engine_version(),
          'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
          'scope':'technical terrain collision, coordinate and presentation acceptance fixture; no final visual design',
          'map':'/Game/T4Fixtures/BXW_Integration','meshes':[], 'trace_checks':[], 'passed':False}
target = repo/'test-results/t4-terrain-import.json'
try:
    unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world=unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    static_subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for item in exports['checks']:
        filename = surface / item['fbx'].replace('\\','/')
        asset_path = '/Game/T4Fixtures/Terrain/'+filename.stem
        # Reimport from the hash-recorded FBX on every acceptance run. Matching
        # extents alone cannot prove a previously cached UAsset's source.
        mesh = None
        if mesh is None:
            task = unreal.AssetImportTask()
            task.filename=str(filename);task.destination_path='/Game/T4Fixtures/Terrain'
            task.automated=True;task.save=True;task.replace_existing=True
            options=unreal.FbxImportUI()
            options.import_mesh=True;options.import_as_skeletal=False
            options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
            options.import_materials=False;options.import_textures=False
            data=options.static_mesh_import_data
            data.combine_meshes=False;data.auto_generate_collision=False
            data.import_uniform_scale=1.0;data.convert_scene=True;data.convert_scene_unit=True
            data.force_front_x_axis=False;data.generate_lightmap_u_vs=False
            task.options=options
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            mesh=next(obj for obj in task.get_objects() if isinstance(obj,unreal.StaticMesh))
        body=mesh.get_editor_property('body_setup')
        body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        p=item['actor_pose_map_m']
        actor=actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(p[0]*100,-p[1]*100,p[2]*100))
        actor.set_actor_label('T4_DERIVED_'+item['id'])
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        actor.static_mesh_component.set_simulate_physics(False)
        box=mesh.get_bounding_box();delta=box.max-box.min
        expected=[v*100 for v in item['dimensions_m']]
        actual=[delta.x,delta.y,delta.z]
        error=max(abs(a-b) for a,b in zip(actual,expected))
        if error>.1:raise RuntimeError('Mesh units changed: '+item['id'])
        report['meshes'].append({'id':item['id'],'fbx_sha256':hashlib.sha256(filename.read_bytes()).hexdigest(),
                                 'asset':mesh.get_path_name(),'pose_map_m':p,'dimensions_cm':actual,'max_dimension_error_cm':error,
                                 'triangles':mesh.get_num_triangles(0),'collision':'complex triangles; query only; no physics'})
    # Presentation-only cube. No control or physics component is enabled.
    rover_class=unreal.load_class(None,'/Script/RedlineBridge.RedlineRoverActor')
    spawn=manifest['spawn']
    sx,sy,sz=spawn['map_x_m'],spawn['map_y_m'],spawn['ground_z_m']+0.5
    rover=actor_subsystem.spawn_actor_from_class(rover_class,unreal.Vector(sx*100,-sy*100,sz*100))
    rover.set_actor_label('T4_ROS_Authority_Presentation_Cube')
    # Plain engine lighting and an explicit technical camera, without authored materials.
    light=actor_subsystem.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,0),unreal.Rotator(-45,0,0))
    light.set_actor_label('T4_TestLight')
    camera=actor_subsystem.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(14500,30300,-359000),unreal.Rotator(-30,-90,0))
    camera.set_actor_label('T4_InspectionCamera')
    camera.set_editor_property('auto_activate_for_player',unreal.AutoReceiveInput.PLAYER0)
    if not unreal.EditorLoadingAndSavingUtils.save_map(world,report['map']):raise RuntimeError('Cannot save fixture map')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for point in manifest['qa']['three_point_test']:
        x,y,z=point['map_x_m'],point['map_y_m'],point['dem_bilinear_z_m']
        # UE 5.8 Python does not expose the native-break HitResult helper.
        # A small reflected C++ query reads actual runtime complex collision.
        trace=unreal.RedlineCoords.trace_terrain_height(world,unreal.Vector(x,y,z),100.)
        # Python's UE binding folds bool + one output into Optional[Vector].
        blocking=isinstance(trace,unreal.Vector)
        location=trace if blocking else unreal.Vector()
        measured=location.z
        error=abs(measured-z)
        check={'id':point['id'],'blocking_hit':blocking,'map_xy_m':[x,y],'dem_z_m':z,'trace_z_m':measured,'error_m':error,'passed':blocking and error<=.1}
        report['trace_checks'].append(check)
        if not check['passed']:raise RuntimeError('DEM line trace tolerance exceeded: '+point['id'])
    report['passed']=len(report['meshes'])==17 and len(report['trace_checks'])==3
    subsystem.save_current_level()
except Exception as error:
    report['error']=repr(error)
finally:
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    unreal.log('REDLINE_T4_TERRAIN '+json.dumps(report))
if not report['passed']:raise RuntimeError(report.get('error','fixture incomplete'))
