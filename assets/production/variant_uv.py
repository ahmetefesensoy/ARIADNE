"""Extract only character head/neck UV coverage to protect skin in accent variants."""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'incoming/astronaut/master.blend'),load_ui=False,use_scripts=False)
obj=bpy.data.objects['SK_Astronaut_LOD0'];uv=obj.data.uv_layers.active
protected={g.index for g in obj.vertex_groups if g.name in ('head','neck_01','neck_02')}
vertices={v.index for v in obj.data.vertices if any(g.group in protected and g.weight>0.05 for g in v.groups)}
polys=[[[float(x) for x in uv.data[li].uv] for li in p.loop_indices] for p in obj.data.polygons if any(v in vertices for v in p.vertices)]
(ROOT/'production/astronaut_skin_uv.json').write_text(json.dumps(polys,separators=(',',':')),encoding='utf-8')
print('SKIN_UV_POLYGONS',len(polys),flush=True)
