"""Rebuild /Game/Prologue/Materials/M_LandingDust so it compiles (playtest 2026-11-15).

The previous graph failed to compile for PCD3D_SM5 in every game launch, so the four 11-17 m
landing-dust planes rendered with the opaque default material. This version is unlit translucent:
opacity = saturate(1 - 4 |uv - 0.5|^2) * DustAmount, a soft disc that the prologue drives through
the same DustAmount parameter. Presentation only; no weather or soil claim.

Run inside the Unreal editor for the build snapshot:
  UnrealEditor-Cmd.exe <Redline.uproject> -ExecutePythonScript=<this file> -unattended -nosplash
"""
import unreal

LIB = unreal.MaterialEditingLibrary
PATH = "/Game/Prologue/Materials/M_LandingDust"

material = unreal.load_asset(PATH)
if material is None:
    raise RuntimeError(f"{PATH} not found")
LIB.delete_all_material_expressions(material)
material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property("two_sided", True)


def node(cls, x, y):
    return LIB.create_material_expression(material, cls, x, y)


color = node(unreal.MaterialExpressionConstant3Vector, -600, -200)
color.set_editor_property("constant", unreal.LinearColor(0.25, 0.10, 0.04, 1.0))
LIB.connect_material_property(color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

uv = node(unreal.MaterialExpressionTextureCoordinate, -900, 100)
center = node(unreal.MaterialExpressionConstant2Vector, -900, 220)
center.set_editor_property("r", 0.5)
center.set_editor_property("g", 0.5)
offset = node(unreal.MaterialExpressionSubtract, -700, 150)
LIB.connect_material_expressions(uv, "", offset, "A")
LIB.connect_material_expressions(center, "", offset, "B")
square = node(unreal.MaterialExpressionDotProduct, -500, 150)
LIB.connect_material_expressions(offset, "", square, "A")
LIB.connect_material_expressions(offset, "", square, "B")
scaled = node(unreal.MaterialExpressionMultiply, -350, 150)
scaled.set_editor_property("const_b", 4.0)
LIB.connect_material_expressions(square, "", scaled, "A")
falloff = node(unreal.MaterialExpressionOneMinus, -200, 150)
LIB.connect_material_expressions(scaled, "", falloff, "")  # single-input pins are unnamed in UE 5.8
soft = node(unreal.MaterialExpressionSaturate, -60, 150)
LIB.connect_material_expressions(falloff, "", soft, "")
amount = node(unreal.MaterialExpressionScalarParameter, -200, 300)
amount.set_editor_property("parameter_name", "DustAmount")
amount.set_editor_property("default_value", 0.0)
opacity = node(unreal.MaterialExpressionMultiply, 100, 200)
LIB.connect_material_expressions(soft, "", opacity, "A")
LIB.connect_material_expressions(amount, "", opacity, "B")
LIB.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)

LIB.recompile_material(material)
unreal.EditorAssetLibrary.save_loaded_asset(material, False)
unreal.log(f"REDLINE fix_landing_dust: rebuilt {PATH} (unlit translucent, DustAmount opacity)")
