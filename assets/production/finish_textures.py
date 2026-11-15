"""Separate PBR channels, record normal conventions and create two suit materials."""
from pathlib import Path
import json
from PIL import Image, ImageOps, ImageDraw
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
for meta in sorted((ROOT/'incoming').glob('*/asset.json')):
    data=json.loads(meta.read_text());folder=meta.parent;channels={}
    for t in data['textures']:
        path=folder/t['path'];name=t['name'].lower()
        if name.startswith('orm') or '_orm' in name or '_arm' in name:
            img=Image.open(path).convert('RGB')
            for idx,ch in enumerate(('AO','Roughness','Metallic')):
                out=folder/'textures'/f"{data['asset_id']}_{ch}.png";img.getchannel(idx).save(out);channels[ch]='textures/'+out.name
        elif 'normal' in name or 'nor_gl' in name:
            img=Image.open(path).convert('RGB');r,g,b=img.split()
            out=folder/'textures'/f"{data['asset_id']}_NormalDX.png"
            Image.merge('RGB',(r,ImageOps.invert(g),b)).save(out)
            channels['NormalGL']=t['path'];channels['NormalDX']='textures/'+out.name
        if t['colorspace']=='sRGB':channels['BaseColor']=t['path']
    bindings_path=folder/'material_bindings.json'
    if bindings_path.exists():
        bindings=json.loads(bindings_path.read_text())
        data['materials']=bindings
        if len(bindings)==1:
            mat=next(iter(bindings.values()))
            for role,key in [('Base Color','BaseColor'),('Normal','NormalGL'),('Roughness','Roughness'),('Metallic','Metallic')]:
                entry=mat.get(role,{})
                if 'path' not in entry:continue
                source=folder/entry['path']
                if not source.is_file():continue
                img=Image.open(source).convert('RGB')
                if entry.get('component') in ('R','G','B'):
                    output=folder/'textures'/f"{data['asset_id']}_{key}.png"
                    img.getchannel(entry['component']).save(output);channels[key]='textures/'+output.name
                else:channels[key]=entry['path']
                if key=='NormalGL':
                    r,g,b=img.split();output=folder/'textures'/f"{data['asset_id']}_NormalDX.png"
                    Image.merge('RGB',(r,ImageOps.invert(g),b)).save(output);channels['NormalDX']='textures/'+output.name
    data['material_channels']=channels
    data['export_settings']={'fbx_binary_version':7400,'blender_axis_forward':'-Y','blender_axis_up':'Z','unit_scale_length':1,'apply_unit_scale':True,'apply_scale_options':'FBX_SCALE_UNITS','obj':'raw metres +X/+Y/+Z, no baked axis change','unreal_import_scale_and_orientation':'NOT_VERIFIED_IN_ENGINE','lod_files':'Separate FBX files; import LOD1/LOD2 explicitly; no automatic LOD-group claim','material_binding':'Connect BaseColor as sRGB; ORM/roughness/metallic/normal as linear; choose NormalDX for Unreal, NormalGL for Blender/glTF; engine binding untested'}
    if data['asset_id']=='astronaut':
        data['collisions']['shapes']='12-segment capsule; static proxy geometry; skeletal PhysicsAsset not created'
        path=folder/channels['BaseColor'];img=Image.open(path).convert('RGB')
        protected=Image.new('L',img.size,0);draw=ImageDraw.Draw(protected)
        for poly in json.loads((ROOT/'production/astronaut_skin_uv.json').read_text()):
            draw.polygon([(round(u*(img.width-1)),round((1-v)*(img.height-1))) for u,v in poly],fill=255)
        arr=np.array(img);r,g,b=arr[:,:,0].astype(float),arr[:,:,1].astype(float),arr[:,:,2].astype(float)
        mask=(r>g*1.6)&(r>b*1.45)&(r>60)&(np.array(protected)==0)
        altered=arr.copy();altered[mask,0]=arr[mask,2];altered[mask,1]=(arr[mask,1].astype(float)*0.95).astype(np.uint8);altered[mask,2]=arr[mask,0]
        out=folder/'textures/astronaut_EV2_BaseColor.png';Image.fromarray(altered).save(out)
        data['material_variants']={'EV1':{'BaseColor':channels['BaseColor'],'accent':'source red'},'EV2':{'BaseColor':'textures/'+out.name,'accent':'scenario blue; head/neck UV region protected','changed_texels':int(mask.sum())},'mesh_and_rig':'Shared; no second human generated'}
    meta.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(data['asset_id'],list(channels),flush=True)
