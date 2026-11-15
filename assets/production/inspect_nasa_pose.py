import bpy,json,sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"incoming/curiosity_reference/source.blend"
bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False)
print("SCENE",bpy.context.scene.frame_current,bpy.context.scene.frame_start,bpy.context.scene.frame_end)
print("ACTIONS",[(a.name,list(a.frame_range)) for a in bpy.data.actions])
for frame in [0,1,30,60,120,180,240,250]:
 bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
 print("POSE",frame,[(bpy.data.objects[n].name,[round(x,3) for x in bpy.data.objects[n].matrix_world.translation]) for n in ["MastCam","wheel_01_R","APXS"]])
