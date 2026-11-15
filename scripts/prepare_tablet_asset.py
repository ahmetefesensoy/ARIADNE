"""Source-preserving Tripo tablet normalization/export, Blender 5.2 CLI."""
import sys, json, hashlib, math
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
repo=Path(sys.argv[sys.argv.index('--')+1])
sys.path.insert(0,str(repo/'scripts'))
from prepare_tripo_prologue_assets import bounds,original_images,materials,select,sha
src=repo/'tripo-out/realistic-rugged-handheld-eva-sc-2ba0f9c0/model.glb'
out=repo/'assets/incoming/field_tablet/prepared';out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
bpy.ops.import_scene.gltf(filepath=str(src))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
lo,hi=bounds(objects);dims=hi-lo
print('SOURCE_TABLET_BOUNDS',list(lo),list(hi),list(dims),flush=True)
# glTF +Y-up becomes Blender +Z-up: the thin depth axis becomes Y.
order=sorted(range(3),key=lambda i:dims[i],reverse=True)
axes=Matrix.Identity(4)
for r,axis in enumerate(order):
    for c in range(3):axes[r][c]=1 if c==axis else 0
if axes.to_3x3().determinant()<0:axes[2][order[2]]=-1
centre=(lo+hi)*.5
normal=Matrix.Diagonal((.32/dims[order[0]],.22/dims[order[1]],.02/dims[order[2]],1))@axes@Matrix.Translation(-centre)
for obj in objects:obj.matrix_world=normal@obj.matrix_world
select(objects);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
if len(objects)>1:bpy.ops.object.join()
obj=bpy.context.view_layer.objects.active;obj.name='SM_FieldTablet';obj.data.name='SM_FieldTablet'
obj.data.calc_loop_triangles();triangles=len(obj.data.loop_triangles)
if triangles>85000:
    mod=obj.modifiers.new('Tablet_budget','DECIMATE');mod.ratio=80000/triangles
    bpy.ops.object.modifier_apply(modifier=mod.name)
textures,paths=original_images([obj],out);binding=materials([obj],paths,'field_tablet')
(out/'material_bindings.json').write_text(json.dumps(binding,indent=2))
select([obj]);bpy.ops.export_scene.fbx(filepath=str(out/'field_tablet.fbx'),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',bake_anim=False,path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'field_tablet.blend'))
lo,hi=bounds([obj]);obj.data.calc_loop_triangles()
report={'schema':'redline.tablet.asset.v1','source_task_id':'2ba0f9c0-286a-4899-8487-f1ca42345949',
 'status':'SCENARIO','source':str(src.relative_to(repo)),'source_sha256':sha(src),'source_bounds':list(dims),
 'source_to_canonical_matrix':[list(row) for row in normal], 'dimensions_m':list(hi-lo),
 'triangles':len(obj.data.loop_triangles),'uv_layers':len(obj.data.uv_layers),'textures':textures,
 'fbx_sha256':sha(out/'field_tablet.fbx'),'note':'Authored dimensions; generated visual, not real mission hardware. Original model preserved.'}
(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
