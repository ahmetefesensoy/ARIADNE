"""Read back imported EV1 materials, skeletons and animation tracks in UE."""
import json
import os
from pathlib import Path
import unreal

out = {}
mesh = unreal.load_asset('/Game/EVAFixtures/Astronaut/SK_Astronaut')
out['mesh_skeleton'] = mesh.skeleton.get_path_name() if mesh and mesh.skeleton else None
out['slots'] = [str(s.material_interface.get_path_name()) if s.material_interface else None for s in mesh.materials]
for name in ('AN_Idle','AN_Walk'):
    anim = unreal.load_asset('/Game/EVAFixtures/Astronaut/'+name)
    tracks = unreal.AnimationLibrary.get_animation_track_names(anim)
    out[name] = {'skeleton': anim.get_editor_property('skeleton').get_path_name() if anim.get_editor_property('skeleton') else None,
                 'length': anim.get_play_length(), 'tracks': [str(t) for t in tracks]}
mat = unreal.load_asset('/Game/EVAFixtures/M_EV1_Original')
out['material_usage_skeletal'] = mat.get_editor_property('used_with_skeletal_mesh')
out['material_inputs'] = {}
for name, prop in [('color',unreal.MaterialProperty.MP_BASE_COLOR),('normal',unreal.MaterialProperty.MP_NORMAL),
                   ('metallic',unreal.MaterialProperty.MP_METALLIC),('roughness',unreal.MaterialProperty.MP_ROUGHNESS),
                   ('ao',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)]:
    node = unreal.MaterialEditingLibrary.get_material_property_input_node(mat,prop)
    out['material_inputs'][name] = {'node':node.get_class().get_name() if node else None,
        'texture': node.texture.get_path_name() if node and isinstance(node,unreal.MaterialExpressionTextureSample) and node.texture else None}
(Path(os.environ['REDLINE_REPO'])/'test-results/eva-import-diagnosis.json').write_text(json.dumps(out,indent=2)+'\n')
unreal.log('EVA_DIAG '+json.dumps(out))
