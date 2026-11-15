"""Read actual shader node connections; names alone do not establish PBR channels."""
from pathlib import Path
import json
import bpy

ROOT=Path(__file__).resolve().parents[1]

def trace(socket,channel=None,visited=None):
    if not socket.is_linked:return {'constant':list(socket.default_value) if hasattr(socket.default_value,'__len__') else socket.default_value}
    visited=set() if visited is None else visited
    link=socket.links[0];node=link.from_node
    if node in visited:return {'unresolved':'cycle'}
    visited.add(node)
    if node.type=='TEX_IMAGE' and node.image:
        return {'image':node.image.name,'path':'textures/'+Path(node.image.filepath_raw).name,'component':channel or 'RGB','colorspace':node.image.colorspace_settings.name}
    if node.type in ('SEPARATE_COLOR','SEPRGB'):
        component={'Red':'R','Green':'G','Blue':'B','R':'R','G':'G','B':'B'}.get(link.from_socket.name)
        return trace(node.inputs[0],component,visited)
    if node.type=='NORMAL_MAP':return {**trace(node.inputs['Color'],channel,visited),'normal_convention':'OpenGL','strength':node.inputs['Strength'].default_value}
    return {'unresolved':node.type,'upstream':[trace(s,channel,visited.copy()) for s in node.inputs if s.is_linked]}

for meta in sorted((ROOT/'incoming').glob('*/asset.json')):
    folder=meta.parent
    data=json.loads(meta.read_text())
    image_paths={t['name']:t['path'] for t in data['textures']}
    bpy.ops.wm.open_mainfile(filepath=str(folder/'master.blend'),load_ui=False,use_scripts=False)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('SM_') or o.name.startswith('SK_')) and o.name.endswith('LOD0')]
    mats={m for o in objects for m in o.data.materials if m}
    result={}
    for mat in mats:
        if not mat.use_nodes:continue
        bsdf=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if not bsdf:continue
        result[mat.name]={name:trace(bsdf.inputs[name]) for name in ('Base Color','Roughness','Metallic','Normal')}
        for entry in result[mat.name].values():
            if entry.get('image') in image_paths:entry['path']=image_paths[entry['image']]
    (folder/'material_bindings.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('MATERIAL_BINDINGS',folder.name,len(result),flush=True)
