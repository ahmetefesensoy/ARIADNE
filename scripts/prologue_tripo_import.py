"""Unreal editor helpers for source-preserving Tripo prologue derivatives."""
import hashlib
import json
import unreal


def import_file(path, destination, name, options=None):
    task = unreal.AssetImportTask()
    task.filename,task.destination_path,task.destination_name = str(path),destination,name
    task.automated = task.replace_existing = True
    task.save = False
    if options:task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_objects())


def texture_material(root, dest, name, path, unlit=False):
    tools = unreal.AssetToolsHelpers.get_asset_tools();lib = unreal.MaterialEditingLibrary
    tex = next(o for o in import_file(path,dest+'/Textures','T_'+name) if isinstance(o,unreal.Texture2D))
    mat = unreal.load_asset(dest+'/Materials/M_'+name)
    if not mat:mat = tools.create_asset('M_'+name,dest+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(mat)
    sample = lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample);sample.texture = tex
    lib.connect_material_property(sample,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
    rough = lib.create_material_expression(mat,unreal.MaterialExpressionConstant);rough.r = .55
    lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    # The Mars exterior uses physical exposure; modest paper glow keeps print
    # legible under the motivated cabin light without altering source pixels.
    if unlit:
        gain = lib.create_material_expression(mat,unreal.MaterialExpressionMultiply)
        amount = lib.create_material_expression(mat,unreal.MaterialExpressionConstant);amount.r = 180
        lib.connect_material_expressions(sample,'RGB',gain,'A');lib.connect_material_expressions(amount,'',gain,'B')
        lib.connect_material_property(gain,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mat.set_editor_property('two_sided',True)
    lib.recompile_material(mat)
    for asset in (tex,mat):unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
    return mat


def import_visual(root, asset_id, dest, report):
    directory = root/'data/engines/prologue-tripo-v1'/asset_id
    manifest = json.loads((directory/'manifest.json').read_text())
    if not manifest['passed']:raise RuntimeError('Unvalidated model '+asset_id)
    export = next(e for e in manifest['exports'] if e['kind']=='FBX' and e['lod']==0)
    path = directory/export['file']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=export['sha256']:raise RuntimeError('Derivative changed '+asset_id)
    ui = unreal.FbxImportUI();ui.automated_import_should_detect_type = False
    ui.import_mesh = True;ui.import_as_skeletal = ui.import_materials = ui.import_textures = False
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = ui.static_mesh_import_data
    data.combine_meshes = True;data.auto_generate_collision = False
    data.convert_scene = data.convert_scene_unit = data.transform_vertex_to_absolute = True
    data.force_front_x_axis = data.generate_lightmap_u_vs = False
    mesh = next(o for o in import_file(path,dest+'/Tripo','SM_'+asset_id,ui) if isinstance(o,unreal.StaticMesh))
    bindings = json.loads((directory/'material_bindings.json').read_text())
    mats = {}
    for name,binding in bindings.items():
        channel = binding['channels']['Base Color']
        if 'path' not in channel:raise RuntimeError('Missing original base-color map '+name)
        mats[name] = texture_material(root,dest,name,directory/channel['path'])
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        match = next((name for name in mats if name in str(slot.material_slot_name)),None)
        if not match and len(mats)==1:match = next(iter(mats))
        if not match:raise RuntimeError('Unknown imported material slot '+str(slot.material_slot_name))
        mesh.set_material(i,mats[match])
    if asset_id in ('prologue_command','prologue_lab','prologue_corridor'):
        if not unreal.RedlineEVAImportLibrary.prepare_interior_query_collision(mesh):raise RuntimeError('Interior query collision could not be built '+asset_id)
    box = mesh.get_bounding_box();size = box.max-box.min
    errors = [abs(a-b*100) for a,b in zip((size.x,size.y,size.z),manifest['dimensions_m'])]
    if max(errors)>.1:raise RuntimeError('Engine scale mismatch '+asset_id+': '+str(errors))
    unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
    report.setdefault('tripo_assets',[]).append({'id':asset_id,'manifest':str((directory/'manifest.json').relative_to(root)),
        'source_sha256':manifest['source_sha256'],'dimensions_cm':[size.x,size.y,size.z],
        'unit_error_cm':max(errors),'triangles':mesh.get_num_triangles(0),'physics':False})
    return mesh
