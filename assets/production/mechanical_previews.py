"""Record static neutral/quarter-turn inspection views; no controller is authored."""
from pathlib import Path
import sys,math,json
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from preview import views

for aid in ('rover_1','pr_1','scout_1'):
    folder=ROOT/'incoming'/aid
    bpy.ops.wm.open_mainfile(filepath=str(folder/'master.blend'),load_ui=False,use_scripts=False)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('SM_') and o.name.endswith('LOD0')]
    rotating=[o for o in objects if any(s in o.name for s in ('wheel','rotor'))]
    records=[]
    for o in rotating:
        before=o.matrix_world.translation.copy()
        point_before=o.matrix_world@o.data.vertices[0].co
        o.rotation_mode='XYZ'
        o.rotation_euler.rotate_axis('Y' if 'wheel' in o.name else 'Z',math.pi/2)
        bpy.context.view_layer.update()
        records.append({'part':o.name,'angle_deg':90,'pivot_m':list(before),'pivot_drift_m':(o.matrix_world.translation-before).length,'vertex_displacement_m':(o.matrix_world@o.data.vertices[0].co-point_before).length})
    views(objects,folder/'preview/quarter_turn',('perspective','front'),640)
    (folder/'pivot_checks.json').write_text(json.dumps({'method':'Rotate separate wheel/rotor visuals by 90 degrees; check origin stays fixed; inspect renders','records':records,'engine_joint_binding':'NOT_RUN'},indent=2)+'\n',encoding='utf-8')
    print('PIVOT_PREVIEWS_DONE',aid,len(records),flush=True)
