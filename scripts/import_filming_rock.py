"""Import approved rock art at source scale; no level/physics changes."""
import hashlib,json,os
from pathlib import Path
import unreal
root=Path(os.environ['REDLINE_REPO']);folder=root/'assets/incoming/rock_07';dest='/Game/Filming/Rocks'
tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
def imp(path,name,options=None):
    t=unreal.AssetImportTask();t.filename=str(path);t.destination_path=dest;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True
    if options:t.options=options
    tools.import_asset_tasks([t]);return list(t.get_objects())
unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
ui=unreal.FbxImportUI();ui.automated_import_should_detect_type=False;ui.import_as_skeletal=False;ui.import_materials=False;ui.import_textures=False;ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
data=ui.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True
fbx=folder/'unreal/rock_07_LOD0.fbx';mesh=next(x for x in imp(fbx,'SM_rock_07',ui) if isinstance(x,unreal.StaticMesh))
mat=unreal.load_asset(dest+'/M_rock_07') or tools.create_asset('M_rock_07',dest,unreal.Material,unreal.MaterialFactoryNew());lib.delete_all_material_expressions(mat)
for filename,name,prop,component,srgb,normal in [('rock_07_diff.png','T_rock_color',unreal.MaterialProperty.MP_BASE_COLOR,'RGB',True,False),('rock_07_rough.png','T_rock_rough',unreal.MaterialProperty.MP_ROUGHNESS,'G',False,False),('rock_07_nor_gl.png','T_rock_normal',unreal.MaterialProperty.MP_NORMAL,'RGB',False,True)]:
    tex=next(x for x in imp(folder/'textures'/filename,name) if isinstance(x,unreal.Texture2D));tex.set_editor_property('srgb',srgb)
    if normal:tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    unreal.EditorAssetLibrary.save_loaded_asset(tex,False)
    node=lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample);node.texture=tex;node.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if srgb else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
    lib.connect_material_property(node,component,prop)
lib.recompile_material(mat);mesh.set_material(0,mat);unreal.EditorAssetLibrary.save_loaded_asset(mat,False);unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
meta=json.loads((folder/'asset.json').read_text());box=mesh.get_bounding_box();size=box.max-box.min;actual=[size.x,size.y,size.z];expected=[100*x for x in meta['master']['dimensions_m']];error=max(abs(a-b) for a,b in zip(actual,expected))
report={'passed':error<.1,'mesh_asset':mesh.get_path_name(),'dimensions_cm':actual,'unit_error_cm':error,'source_fbx_sha256':hashlib.sha256(fbx.read_bytes()).hexdigest(),'source_notice':'assets/incoming/rock_07/SOURCE.md','status':'SCENARIO','limits':'Source texture colour only; no imported Blender vertex-colour multiply. Presentation has no robot collision authority.'}
(root/'test-results/filming-rock-import.json').write_text(json.dumps(report,indent=2)+'\n')
if not report['passed']:raise RuntimeError('Rock scale differs from Gazebo source')
