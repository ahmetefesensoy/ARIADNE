"""Read-only saved-map reload: terrain poses, source triangles and DEM traces."""
from datetime import datetime,timezone
import hashlib,json,os,traceback
from pathlib import Path
import unreal
root=Path(os.environ['REDLINE_REPO']).resolve();manifest_path=root/'data/engines/BXW/surface-v2-1m/manifest.json'
manifest=json.loads(manifest_path.read_text());target='/Game/EVAFixtures/BXW_EVA_SurfaceV2'
report={'schema':'redline.surface.saved_scene.v2','created_at_utc':datetime.now(timezone.utc).isoformat(),'map':target,'passed':False,
    'scope':'Saved map reload and actual collision; no GPU frame/performance acceptance','meshes':[],'trace_checks':[]}
try:
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(target):raise RuntimeError('Saved map missing')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    terrain=[a for a in actors if a.actor_has_tag('redline_surface_v2')]
    if len(terrain)!=len(manifest['meshes']):raise RuntimeError('Saved terrain count differs')
    by_id={a.get_actor_label().removeprefix('DERIVED_BXW_V2_'):a for a in terrain}
    for tile in manifest['meshes']:
        actor=by_id[tile['id']];p=tile['pose_map_m'];v=actor.get_actor_location()
        pose_error=max(abs(a-b) for a,b in zip([v.x,v.y,v.z],[100*p[0],-100*p[1],100*p[2]]))
        comp=actor.static_mesh_component;mesh=comp.get_editor_property('static_mesh')
        if pose_error>.01 or mesh.get_num_triangles(0)!=tile['triangles']:raise RuntimeError('Saved pose/geometry mismatch '+tile['id'])
        if not comp.get_material(0).get_path_name().startswith('/Game/VisualShowcase/Materials/M_ScenarioSand_context.'):raise RuntimeError('Context material changed')
        if comp.is_simulating_physics():raise RuntimeError('Terrain unexpectedly simulates')
        report['meshes'].append({'id':tile['id'],'pose_error_cm':pose_error,'triangles':mesh.get_num_triangles(0),'asset':mesh.get_path_name()})
    for p in manifest['qa']['three_point_test']:
        hit=unreal.RedlineCoords.trace_terrain_height(world,unreal.Vector(p['map_x_m'],p['map_y_m'],p['dem_bilinear_z_m']),100.)
        error=abs(hit.z-p['dem_bilinear_z_m']) if isinstance(hit,unreal.Vector) else None
        check={'id':p['id'],'dem_z_m':p['dem_bilinear_z_m'],'trace_z_m':hit.z if isinstance(hit,unreal.Vector) else None,'error_m':error,'passed':error is not None and error<=.1}
        report['trace_checks'].append(check)
        if not check['passed']:raise RuntimeError('Saved map DEM trace failed '+p['id'])
    report.update(passed=True,total_scene_actors=len(actors),source_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest())
except Exception as error:report.update(error=repr(error),traceback=traceback.format_exc())
finally:
    (root/'test-results/surface-v2-saved-scene.json').write_text(json.dumps(report,indent=2)+'\n')
    unreal.log('REDLINE_SURFACE_V2_SAVED '+json.dumps(report))
if not report['passed']:raise RuntimeError(report.get('error','verification incomplete'))
