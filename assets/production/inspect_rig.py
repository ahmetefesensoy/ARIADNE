import bpy,json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"incoming/astronaut/master.blend"
bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False)
print("FPS",bpy.context.scene.render.fps)
for o in bpy.context.scene.objects:
 if o.type=="ARMATURE":
  print("ARM",o.name,"mode",o.data.pose_position,"action",o.animation_data.action.name if o.animation_data and o.animation_data.action else None)
  if o.animation_data:
   print("NLA",[(t.name,t.mute,[(s.name,s.action.name if s.action else None,s.frame_start,s.frame_end) for s in t.strips]) for t in o.animation_data.nla_tracks])
print("ACTIONS",[(a.name,list(a.frame_range),[(s.identifier,s.target_id_type) for s in a.slots]) for a in bpy.data.actions])
