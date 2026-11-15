"""Preserve measured DEM vertices; add context-atlas UVs and metre-scale FBX.

Blender CLI: --background --python this.py -- --surface DIR --out NEW_DIR
No generated terrain detail or changes to source OBJ are made. Each tile is
released before the next to bound memory; the original manifest remains source.
"""
import argparse
from datetime import datetime, timezone
import hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dims(obj):
    p=[obj.matrix_world@Vector(v) for v in obj.bound_box]
    return [max(v[i] for v in p)-min(v[i] for v in p) for i in range(3)]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--surface',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);source=a.surface.resolve();out=a.out.resolve()
    manifest_path=source/'manifest.json';manifest=json.loads(manifest_path.read_text())
    if manifest['frame']!='map' or manifest['units']!='m' or manifest['status']!='DERIVED':raise ValueError('Unexpected source frame/status')
    out.mkdir(parents=True,exist_ok=True);(out/'fbx').mkdir(exist_ok=True)
    report={'schema':'redline.surface.fbx.v2','created_at_utc':datetime.now(timezone.utc).isoformat(),'source_manifest':str(manifest_path),
        'source_manifest_sha256':sha(manifest_path),'helper_sha256':sha(Path(__file__)),'status':'DERIVED','master_units':'metres; ENU',
        'uv_contract':'U=(map_x+1500)/3000; V=(map_y+1500)/3000; north-up context atlas; source imagery unchanged',
        'texture_source':'surface-v1/atlas_context.png','blender':bpy.app.version_string,'checks':[],'passed':False}
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    for tile in manifest['meshes']:
        original=source/tile['relative_path']
        if sha(original)!=tile['sha256']:raise ValueError('Source hash mismatch '+tile['id'])
        bpy.ops.wm.obj_import(filepath=str(original),forward_axis='Y',up_axis='Z')
        objects=[o for o in bpy.context.selected_objects if o.type=='MESH']
        if len(objects)!=1:raise ValueError('One tile must be one mesh')
        obj=objects[0];obj.name='SM_BXW_V2_'+tile['id'];mesh=obj.data
        if mesh.validate(verbose=True) or len(mesh.polygons)!=tile['triangles']:raise ValueError('Source topology changed')
        if any(len(f.vertices)!=3 for f in mesh.polygons):raise ValueError('Non triangle')
        size=dims(obj);expected=[tile['bounds_map_m'][2]-tile['bounds_map_m'][0],tile['bounds_map_m'][3]-tile['bounds_map_m'][1],tile['z_bounds_map_m'][1]-tile['z_bounds_map_m'][0]]
        if max(abs(x-y) for x,y in zip(size,expected))>.001:raise ValueError('Metre/axis mismatch '+tile['id'])
        uv=mesh.uv_layers.new(name='UV_Context');px,py=tile['pose_map_m'][:2]
        # The OBJ is local ENU. UVs refer to the existing 3 km context image,
        # not the old 1 km operations atlas that would stretch outside its area.
        for loop in mesh.loops:
            v=mesh.vertices[loop.vertex_index].co;uv.data[loop.index].uv=((v.x+px+1500)/3000,(v.y+py+1500)/3000)
        filename=out/'fbx'/(obj.name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(filename),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=False,bake_anim=False,path_mode='RELATIVE',embed_textures=False)
        report['checks'].append({'id':tile['id'],'fbx':str(filename.relative_to(out)).replace('\\','/'),'fbx_sha256':sha(filename),
            'source_obj_sha256':tile['sha256'],'triangles':tile['triangles'],'vertices':len(mesh.vertices),'dimensions_m':size,
            'actor_pose_map_m':tile['pose_map_m'],'first_vertex_m':list(mesh.vertices[0].co),'uv0':list(uv.data[0].uv),'passed':True})
        print('SURFACE_V2_FBX',len(report['checks']),len(manifest['meshes']),tile['id'],flush=True)
        bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
        (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    report['passed']=len(report['checks'])==len(manifest['meshes'])
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
