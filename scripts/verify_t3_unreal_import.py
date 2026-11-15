"""Unreal Python commandlet: import two representative terrain FBXs and measure cm."""
from datetime import datetime, timezone
import json
from pathlib import Path
import unreal

root=Path(__file__).resolve().parent.parent
source=root/'data/engines/BXW/surface-blender-v1'
target=root/'test-results/t3-unreal-import.json'
verification=json.loads((source/'verification.json').read_text())
report={'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'engine':unreal.SystemLibrary.get_engine_version(),'passed':False,'checks':[],
        'scope':'FBX import and geometry/unit/UV/material checks; no gameplay, ROS bridge or rendered UE scene'}
try:
    # Select the documented FBXImportUI importer explicitly for reproducibility.
    unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    for item in (verification['checks'][0],verification['checks'][-1]):
        task=unreal.AssetImportTask();task.filename=str(source/item['fbx'])
        task.destination_path='/Game/T3TerrainProbeV2';task.automated=True;task.save=True;task.replace_existing=False
        options=unreal.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False
        options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
        options.import_materials=True;options.import_textures=True
        data=options.static_mesh_import_data;data.combine_meshes=False;data.auto_generate_collision=False
        data.import_uniform_scale=1.0;data.convert_scene=True;data.convert_scene_unit=True
        data.force_front_x_axis=False;data.generate_lightmap_u_vs=False
        task.options=options
        known=task.destination_path+'/'+Path(task.filename).stem
        existing=unreal.load_asset(known)
        if existing:objects=[existing]
        else:
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            objects=task.get_objects()
        meshes=[o for o in objects if isinstance(o,unreal.StaticMesh)]
        if len(meshes)!=1:raise RuntimeError(f'Expected one static mesh, got {len(meshes)}')
        mesh=meshes[0];box=mesh.get_bounding_box();extent=box.max-box.min
        actual=[float(extent.x),float(extent.y),float(extent.z)]
        expected=[100*v for v in item['dimensions_m']]
        error=max(abs(a-b) for a,b in zip(actual,expected))
        description=mesh.get_static_mesh_description(0)
        uv_sample=description.get_vertex_instance_uv(unreal.VertexInstanceID(0),0)
        vertex=description.get_vertex_position(unreal.VertexID(0))
        materials=len(mesh.get_editor_property('static_materials'))
        triangles=mesh.get_num_triangles(0)
        texture_role='context' if item['id']=='coarse_ring' else 'ops'
        texture_task=unreal.AssetImportTask()
        texture_task.filename=str(root/f'data/engines/BXW/surface-v1/atlas_{texture_role}.png')
        texture_task.destination_path='/Game/T3TerrainProbeV2';texture_task.automated=True
        texture_task.save=True;texture_task.replace_existing=False
        texture=unreal.load_asset(texture_task.destination_path+'/atlas_'+texture_role)
        if texture is None:
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([texture_task])
            texture=next(o for o in texture_task.get_objects() if isinstance(o,unreal.Texture2D))
        material_path='/Game/T3TerrainProbeV2/MAT_BXW_ORBITAL_'+texture_role
        material=unreal.load_asset(material_path)
        if material is None:
            material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                'MAT_BXW_ORBITAL_'+texture_role,'/Game/T3TerrainProbeV2',unreal.Material,unreal.MaterialFactoryNew())
            sample=unreal.MaterialEditingLibrary.create_material_expression(material,unreal.MaterialExpressionTextureSample,-300,0)
            sample.texture=texture
            unreal.MaterialEditingLibrary.connect_material_property(sample,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
            rough=unreal.MaterialEditingLibrary.create_material_expression(material,unreal.MaterialExpressionConstant,-300,200)
            rough.r=1.0
            unreal.MaterialEditingLibrary.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
            unreal.MaterialEditingLibrary.recompile_material(material)
        mesh.set_material(0,material)
        unreal.EditorAssetLibrary.save_loaded_asset(material)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        # NullRHI does not compile a GPU material resource. Inspect the saved
        # base-colour expression graph instead of its GPU-used-texture cache.
        base=unreal.MaterialEditingLibrary.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
        textures=[base.texture] if isinstance(base,unreal.MaterialExpressionTextureSample) and base.texture else []
        # Match the first source vertex to the actual FBX->UE conversion.
        objfile=root/f'data/engines/BXW/surface-v1/{item["id"]}_visual.obj'
        with objfile.open() as stream:
            first=next(line for line in stream if line.startswith('v '))
        x,y,z=map(float,first.split()[1:4]);expected_vertex=[100*x,-100*y,100*z]
        vertex_error=max(abs(a-b) for a,b in zip((vertex.x,vertex.y,vertex.z),expected_vertex))
        check={'id':item['id'],'asset':mesh.get_path_name(),'bounds_size_cm':actual,
               'expected_bounds_size_cm':expected,'max_dimension_error_cm':error,
               'uv_channel_0_sample':[uv_sample.x,uv_sample.y],
               'vertex_0_cm':[vertex.x,vertex.y,vertex.z],
               'expected_vertex_0_cm':expected_vertex,'vertex_conversion_error_cm':vertex_error,
               'material':material.get_path_name(),'textures':[t.get_path_name() for t in textures],
               'texture_check':'saved BaseColor texture-sample graph; no GPU shader/render claim',
               'triangles':triangles,'material_slots':materials,
               'passed':error<=.1 and triangles==item['triangles'] and materials>=1 and vertex_error<=.1 and texture in textures,
               'imported_objects':[o.get_path_name() for o in objects]}
        report['checks'].append(check)
        if not check['passed']:raise RuntimeError('Unreal terrain scale/UV/material gate failed')
    report['passed']=True
except Exception as error:
    report['error']=str(error)
finally:
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,indent=2)+'\n')
    unreal.log('REDLINE_TERRAIN_IMPORT '+json.dumps(report))
if not report['passed']:raise RuntimeError(report['error'])
