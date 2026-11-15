"""Import source-preserving normalized Tripo tablet, verify UE centimetres."""
import os,json,hashlib,sys
from pathlib import Path
import unreal
root=Path(os.environ['REDLINE_REPO']);sys.path.insert(0,str(root/'scripts'))
from prologue_tripo_import import import_file,texture_material
folder=root/'assets/incoming/field_tablet/prepared';report=json.loads((folder/'manifest.json').read_text())
unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
ui=unreal.FbxImportUI();ui.automated_import_should_detect_type=False;ui.import_mesh=True;ui.import_as_skeletal=False
ui.import_materials=ui.import_textures=False;ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
d=ui.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False
d.convert_scene=d.convert_scene_unit=d.transform_vertex_to_absolute=True;d.generate_lightmap_u_vs=False
mesh=next(o for o in import_file(folder/'field_tablet.fbx','/Game/Campaign/Tablet','SM_FieldTablet',ui) if isinstance(o,unreal.StaticMesh))
bindings=json.loads((folder/'material_bindings.json').read_text())
for i,(name,b) in enumerate(bindings.items()):
    tex=b['channels']['Base Color'];mat=texture_material(root,'/Game/Campaign','TabletOriginal',folder/tex['path'])
    for slot in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(slot,mat)
box=mesh.get_bounding_box();size=box.max-box.min
err=max(abs(a-b*100) for a,b in zip((size.x,size.y,size.z),report['dimensions_m']))
if err>.15:raise RuntimeError('Tablet scale mismatch '+str(err))
unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
meta={'schema':'redline.tablet.asset.v1','mesh_asset':mesh.get_path_name(),'dimensions_cm':[size.x,size.y,size.z],
 'screen_size_cm':[25.2,15.8],'screen_center_cm':[0,0,1.15],'source_task_id':report['source_task_id'],
 'source_sha256':report['source_sha256'],'unit_error_cm':err,'status':'SCENARIO','passed':True}
(Path(unreal.Paths.project_content_dir())/'Campaign/tablet.json').write_text(json.dumps(meta,indent=2)+'\n')
(root/'test-results/tablet-import.json').write_text(json.dumps(meta,indent=2)+'\n')
