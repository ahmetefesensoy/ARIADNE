from pathlib import Path
import sys,json
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from preview import views

folder=ROOT/'incoming/astronaut'
bpy.ops.wm.open_mainfile(filepath=str(folder/'master.blend'),load_ui=False,use_scripts=False)
obj=bpy.data.objects['SK_Astronaut_LOD0']
for mat in obj.data.materials:
    for n in mat.node_tree.nodes:
        if n.type=='TEX_IMAGE' and n.image and n.image.colorspace_settings.name=='sRGB':
            n.image=bpy.data.images.load(str(folder/'textures/astronaut_EV2_BaseColor.png'))
views([obj],folder/'preview/EV2',('perspective','front'),640)
print('EV2_PREVIEW_DONE',flush=True)
