"""Create an unlit campaign-only monitor; leave the original cabin materials intact."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import unreal

root = Path(os.environ["REDLINE_REPO"])
path = "/Game/Campaign/Materials"
name = "M_CampaignDisplay"
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
material = unreal.load_asset(path + "/" + name) or tools.create_asset(
    name, path, unreal.Material, unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(material)
material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property("two_sided", True)
texture = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
texture.set_editor_property("parameter_name", "DisplayMap")
texture.texture = unreal.load_asset("/Engine/EngineResources/DefaultTexture.DefaultTexture")
gain = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
gain.set_editor_property("parameter_name", "DisplayGain")
gain.set_editor_property("default_value", 800.)
fresh = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
fresh.set_editor_property("parameter_name", "DataFresh")
fresh.set_editor_property("default_value", 0.)
multiply = lib.create_material_expression(material, unreal.MaterialExpressionMultiply)
visible = lib.create_material_expression(material, unreal.MaterialExpressionMultiply)
lib.connect_material_expressions(texture, "RGB", multiply, "A")
lib.connect_material_expressions(gain, "", multiply, "B")
lib.connect_material_expressions(multiply, "", visible, "A")
lib.connect_material_expressions(fresh, "", visible, "B")
lib.connect_material_property(visible, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
lib.recompile_material(material)
saved = unreal.EditorAssetLibrary.save_loaded_asset(material, False)
passed = bool(saved and material.get_editor_property("shading_model") == unreal.MaterialShadingModel.MSM_UNLIT)
report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "passed": passed,
          "asset": material.get_path_name(), "shading": "UNLIT", "two_sided": True,
          "purpose": "Readable live campaign wall without specular glare; runtime flips the wall U direction",
          "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(root/"test-results/campaign-display-material.json").write_text(json.dumps(report, indent=2)+"\n")
if not passed:
    raise RuntimeError("Campaign display material was not saved as unlit")
