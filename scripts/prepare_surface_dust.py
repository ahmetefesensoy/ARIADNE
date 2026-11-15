"""Create a soft, low-opacity SCENARIO dust material for pooled native quads.

No texture downloads, particle plugin assets, source terrain changes or weather
measurements. Lighting comes from the existing scene; this is not soil physics.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import unreal

root=Path(os.environ["REDLINE_REPO"])
dest="/Game/Campaign/Materials"
tools=unreal.AssetToolsHelpers.get_asset_tools()
lib=unreal.MaterialEditingLibrary
material=unreal.load_asset(dest+"/M_SurfaceDust") or tools.create_asset(
    "M_SurfaceDust",dest,unreal.Material,unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(material)
material.set_editor_property("blend_mode",unreal.BlendMode.BLEND_TRANSLUCENT)
material.set_editor_property("two_sided",True)
material.set_editor_property("shading_model",unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
material.set_editor_property("translucency_lighting_mode",unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
color=lib.create_material_expression(material,unreal.MaterialExpressionConstant3Vector)
color.set_editor_property("constant",unreal.LinearColor(.25,.105,.038,1))
lib.connect_material_property(color,"",unreal.MaterialProperty.MP_BASE_COLOR)
rough=lib.create_material_expression(material,unreal.MaterialExpressionConstant);rough.r=.95
lib.connect_material_property(rough,"",unreal.MaterialProperty.MP_ROUGHNESS)
uv=lib.create_material_expression(material,unreal.MaterialExpressionTextureCoordinate)
opacity=lib.create_material_expression(material,unreal.MaterialExpressionScalarParameter)
opacity.set_editor_property("parameter_name","PuffOpacity");opacity.set_editor_property("default_value",0.)
mask=lib.create_material_expression(material,unreal.MaterialExpressionCustom)
mask.set_editor_property("output_type",unreal.CustomMaterialOutputType.CMOT_FLOAT1)
mask.set_editor_property("code","""
float2 p=UV.xy*2-1;
float edge=saturate(1-dot(p,p));
float grain=.76+.24*sin(p.x*13+p.y*7)*sin(p.y*11-p.x*5);
return edge*edge*grain*saturate(Opacity);
""")
inputs=[]
for name in ("UV","Opacity"):
    value=unreal.CustomInput();value.set_editor_property("input_name",name);inputs.append(value)
mask.set_editor_property("inputs",inputs)
lib.connect_material_expressions(uv,"",mask,"UV")
lib.connect_material_expressions(opacity,"",mask,"Opacity")
fade=lib.create_material_expression(material,unreal.MaterialExpressionDepthFade)
fade.set_editor_property("fade_distance_default",30.)
lib.connect_material_expressions(mask,"",fade,"Opacity")
lib.connect_material_property(fade,"",unreal.MaterialProperty.MP_OPACITY)
lib.recompile_material(material)
saved=unreal.EditorAssetLibrary.save_loaded_asset(material,False)
report={"created_at_utc":datetime.now(timezone.utc).isoformat(),"passed":bool(saved),
        "asset":material.get_path_name(),"status":"SCENARIO","renderer":"native pooled soft quads; not Niagara",
        "opacity_runtime_cap":.14,"pool_capacity":96,"maximum_lifetime_s":1.25,
        "wind":"authored visual drift, not measured Mars weather",
        "source_script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(root/"test-results/surface-dust-material.json").write_text(json.dumps(report,indent=2)+"\n")
if not saved:raise RuntimeError("Surface dust material was not saved")
