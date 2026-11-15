"""Inspect actual disconnected geometry of the NASA SEV derivative."""
from pathlib import Path
import json
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/"incoming/pr_1/source.glb"))
o=next(o for o in bpy.context.scene.objects if o.type=="MESH")
bm=bmesh.new();bm.from_mesh(o.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00001)
bm.verts.ensure_lookup_table()
bm.verts.index_update()
unseen=set(bm.verts)
report=[]
while unseen:
    v=unseen.pop(); group=[v]; queue=[v]
    while queue:
        v=queue.pop()
        for e in v.link_edges:
            x=e.other_vert(v)
            if x in unseen:
                unseen.remove(x);queue.append(x);group.append(x)
    if len(group)<20:continue
    points=[o.matrix_world @ v.co for v in group]
    low=[min(p[i] for p in points) for i in range(3)]
    high=[max(p[i] for p in points) for i in range(3)]
    report.append({'vertices':len(group),'min':low,'max':high,'center':[(a+b)/2 for a,b in zip(low,high)],'size':[b-a for a,b in zip(low,high)]})
report.sort(key=lambda v:v['vertices'],reverse=True)
(ROOT/'production/sev_components.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for m in report[:70]:print(m['vertices'],[round(v,3) for v in m['center']],[round(v,3) for v in m['size']],flush=True)
bm.free()
