"""Evaluate each delivered character clip separately, render evidence and export FBX."""
from pathlib import Path
import json,math,sys
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from preview import views
from build_package import select

folder=ROOT/'incoming/astronaut'
bpy.ops.wm.open_mainfile(filepath=str(folder/'master.blend'),load_ui=False,use_scripts=False)
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name=='SK_Astronaut_LOD0')
arm.data.pose_position='POSE'
for track in arm.animation_data.nla_tracks:track.mute=True
report={}
for action in list(bpy.data.actions):
    if action.name not in ('idle','walk'):continue
    arm.animation_data.action=action
    if action.slots:arm.animation_data.action_slot=action.slots[0]
    lo,hi=action.frame_range
    frame_ids=[round(lo+(hi-lo)*t) for t in (0.05,0.25,0.5,0.75)]
    samples=[]
    for index,frame in enumerate(frame_ids):
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        coords=np.empty(len(evaluated.data.vertices)*3)
        evaluated.data.vertices.foreach_get('co',coords)
        samples.append({'frame':frame,'finite':bool(np.isfinite(coords).all()),'vertices':len(evaluated.data.vertices),'min':coords.reshape(-1,3).min(axis=0).tolist(),'max':coords.reshape(-1,3).max(axis=0).tolist()})
        views([mesh],folder/'preview'/action.name/f'{index:02}',('perspective','side'),512)
    scene=bpy.context.scene;scene.frame_start=math.floor(lo);scene.frame_end=math.ceil(hi)
    select([mesh,arm])
    bpy.ops.export_scene.fbx(filepath=str(folder/'unreal'/f'AN_Astronaut_{action.name}.fbx'),use_selection=True,object_types={'MESH','ARMATURE','EMPTY'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,path_mode='COPY')
    report[action.name]={'range':[lo,hi],'samples':samples,'fbx':f'unreal/AN_Astronaut_{action.name}.fbx','visual_acceptance':'Review rendered shoulders/knees/fingers/backpack; no Unreal import performed'}
(folder/'animation_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RIG_ACTIONS_DONE',list(report),flush=True)
