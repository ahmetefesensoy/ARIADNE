"""Create M_WindSand: a light, translucent SCENARIO sand material for the native wind-sand quads.

Base colour is a parameter (default: lit Gale dust tone) with a small emissive share so blown sand
still reads in shade. Opacity is a parameter; edges are soft with a grain pattern. No textures,
no Niagara, no weather data. Run in the editor of a build snapshot:
  UnrealEditor-Cmd.exe <Redline.uproject> -ExecutePythonScript=<this file> -unattended -nosplash
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import unreal

root = Path(os.environ.get("REDLINE_REPO", "."))
dest = "/Game/Campaign/Materials"
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
material = unreal.load_asset(dest + "/M_WindSand") or tools.create_asset(
    "M_WindSand", dest, unreal.Material, unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(material)
material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
material.set_editor_property("two_sided", True)
material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
material.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
material.set_editor_property("used_with_static_lighting", False)

color = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter)
color.set_editor_property("parameter_name", "SandColor")
color.set_editor_property("default_value", unreal.LinearColor(.62, .40, .24, 1))
lib.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
glow = lib.create_material_expression(material, unreal.MaterialExpressionMultiply)
glow_k = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
glow_k.set_editor_property("parameter_name", "SandGlow")
glow_k.set_editor_property("default_value", .18)
lib.connect_material_expressions(color, "", glow, "A")
lib.connect_material_expressions(glow_k, "", glow, "B")
lib.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
rough = lib.create_material_expression(material, unreal.MaterialExpressionConstant)
rough.r = .95
lib.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

uv = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate)
opacity = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
opacity.set_editor_property("parameter_name", "PuffOpacity")
opacity.set_editor_property("default_value", 0.)
mask = lib.create_material_expression(material, unreal.MaterialExpressionCustom)
mask.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
mask.set_editor_property("code", """
float2 p=UV.xy*2-1;
float edge=saturate(1-dot(p,p));
float2 g=floor(UV.xy*float2(48,12));
float grain=.55+.45*frac(sin(dot(g,float2(12.9898,78.233)))*43758.5453);
return edge*edge*grain*saturate(Opacity);
""")
inputs = []
for name in ("UV", "Opacity"):
    value = unreal.CustomInput()
    value.set_editor_property("input_name", name)
    inputs.append(value)
mask.set_editor_property("inputs", inputs)
lib.connect_material_expressions(uv, "", mask, "UV")
lib.connect_material_expressions(opacity, "", mask, "Opacity")
fade = lib.create_material_expression(material, unreal.MaterialExpressionDepthFade)
fade.set_editor_property("fade_distance_default", 40.)
lib.connect_material_expressions(mask, "", fade, "Opacity")
lib.connect_material_property(fade, "", unreal.MaterialProperty.MP_OPACITY)
lib.recompile_material(material)
saved = unreal.EditorAssetLibrary.save_loaded_asset(material, False)
report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "passed": bool(saved),
          "asset": material.get_path_name(), "status": "SCENARIO", "renderer": "native pooled soft quads; not Niagara",
          "wind": "authored visual sand, not measured Mars weather",
          "source_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
out = root / "test-results/wind-sand-material.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + "\n")
if not saved:
    raise RuntimeError("Wind sand material was not saved")
