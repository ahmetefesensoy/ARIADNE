from pathlib import Path
import sys,json,numpy as np,bpy
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from build_package import load_nasa
spec=json.loads((ROOT/'incoming/rover_1/asset.json').read_text())
M=np.array(spec['master']['source_to_master_matrix'])
bpy.ops.wm.read_factory_settings(use_empty=True)
objects,src=load_nasa({})
expected={}
for o in objects:
 a=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a)
 transform=M@np.array(o.matrix_world)
 expected[o.name]=a.reshape(-1,3)@transform[:3,:3].T+transform[:3,3]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'incoming/rover_1/master.blend'),load_ui=False,use_scripts=False)
errors=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.name.startswith('SM_') or not o.name.endswith('LOD0'):continue
 key=o.get('source_name');a=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a)
 coords=a.reshape(-1,3)@np.array(o.matrix_world.to_3x3()).T+np.array(o.matrix_world.translation)
 err=np.max(np.linalg.norm(coords-expected[key],axis=1)) if len(coords)==len(expected[key]) else 999
 errors.append({'part':key,'max_vertex_error_m':float(err)})
 if err>0.0001:print('MISMATCH',key,err,'parent',o.parent.name if o.parent else None)
report={'source':'curiosity_reference/source.blend','source_frame':180,'compared_parts':len(errors),'max_vertex_error_m':max(x['max_vertex_error_m'] for x in errors),'pass':all(x['max_vertex_error_m']<0.0001 for x in errors),'parts':errors}
(ROOT/'incoming/rover_1/source_geometry_check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('SOURCE_GEOMETRY',report['pass'],report['compared_parts'],report['max_vertex_error_m'],flush=True)
