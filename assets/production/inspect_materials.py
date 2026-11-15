import bpy,json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'incoming/curiosity_reference/source.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(p),link=False) as (src,dst):dst.objects=src.objects
for o in dst.objects:
 if o and not o.users_collection:bpy.context.scene.collection.objects.link(o)
print('MATERIALS',json.dumps([{'name':m.name,'nodes':[(n.type,getattr(n.image,'name',None) if hasattr(n,'image') else None) for n in m.node_tree.nodes] if m.use_nodes else None} for m in bpy.data.materials]))
print('IMAGES',[(x.name,list(x.size),bool(x.packed_file)) for x in bpy.data.images])
print('HIERARCHY',json.dumps([{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'loc':list(o.location),'rot':list(o.rotation_euler),'hide_render':o.hide_render} for o in bpy.context.scene.objects if o.type=='MESH' and any(x in o.name for x in ['wheel','arm','mast','APXS','DAN'])]))
