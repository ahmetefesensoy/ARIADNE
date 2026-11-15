"""Import approved scout parts/materials; runtime pose remains ROS/Gazebo-owned."""
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import unreal

root=Path(os.environ["REDLINE_REPO"]);dest="/Game/Campaign"
report={"created_at_utc":datetime.now(timezone.utc).isoformat(),"status":"SCENARIO","passed":False,"parts":[]}
def task(path,folder,name,options=None):
    t=unreal.AssetImportTask();t.filename=str(path);t.destination_path=folder;t.destination_name=name
    t.automated=t.replace_existing=True;t.save=False
    if options:t.options=options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);return list(t.get_objects())
try:
    unreal.SystemLibrary.execute_console_command(None,"Interchange.FeatureFlags.Import.FBX 0")
    asset=root/"assets/incoming/scout_1"
    meta=json.loads((asset/"asset.json").read_text());bindings=json.loads((asset/"material_bindings.json").read_text())
    ui=unreal.FbxImportUI();ui.automated_import_should_detect_type=False;ui.import_mesh=True;ui.import_as_skeletal=False
    ui.import_materials=ui.import_textures=False;ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
    d=ui.static_mesh_import_data;d.combine_meshes=False;d.auto_generate_collision=False;d.convert_scene=d.convert_scene_unit=d.transform_vertex_to_absolute=True
    d.generate_lightmap_u_vs=False
    objects=task(asset/"unreal/scout_1_LOD0.fbx",dest+"/Scout","SM_CampaignScout",ui)
    meshes=[o for o in objects if isinstance(o,unreal.StaticMesh)]
    if len(meshes)!=5:raise RuntimeError("Expected body and four separately exported rotors")
    lib=unreal.MaterialEditingLibrary;mats={};texture_cache={}
    properties={"Base Color":unreal.MaterialProperty.MP_BASE_COLOR,"Roughness":unreal.MaterialProperty.MP_ROUGHNESS,
        "Metallic":unreal.MaterialProperty.MP_METALLIC,"Normal":unreal.MaterialProperty.MP_NORMAL}
    for name,channels in bindings.items():
        mat=unreal.load_asset(dest+"/Materials/M_Scout") or unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_Scout",dest+"/Materials",unreal.Material,unreal.MaterialFactoryNew())
        lib.delete_all_material_expressions(mat)
        for channel,entry in channels.items():
            if channel not in properties:continue
            path=entry.get("path")
            if not path:continue
            if path not in texture_cache:
                tex=next(o for o in task(asset/path,dest+"/Textures","T_Scout_"+Path(path).stem) if isinstance(o,unreal.Texture2D))
                tex.set_editor_property("srgb",channel=="Base Color")
                if channel=="Normal":tex.set_editor_property("compression_settings",unreal.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property("flip_green_channel",True)
                unreal.EditorAssetLibrary.save_loaded_asset(tex,False);texture_cache[path]=tex
            tex=texture_cache[path];node=lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample);node.texture=tex
            node.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=="Normal" else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=="Base Color" else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
            lib.connect_material_property(node,entry.get("component","RGB"),properties[channel])
        lib.recompile_material(mat);unreal.EditorAssetLibrary.save_loaded_asset(mat,False);mats[name]=mat
    lower=[float("inf")]*3;upper=[-float("inf")]*3
    for mesh in meshes:
        source=next((p for p in meta["parts"] if p["name"] in mesh.get_name()),None)
        if not source:raise RuntimeError("Unknown imported scout part "+mesh.get_name())
        box=mesh.get_bounding_box()
        for axis,key in enumerate(("x","y","z")):
            lower[axis]=min(lower[axis],getattr(box.min,key));upper[axis]=max(upper[axis],getattr(box.max,key))
        for i in range(len(mesh.get_editor_property("static_materials"))):mesh.set_material(i,next(iter(mats.values())))
        unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
        x,y,z=source["pivot_m"]
        report["parts"].append({"mesh":mesh.get_path_name(),"pivot_cm":[x*100,-y*100,z*100],"rotor":"rotor" in source["source_name"]})
    dimensions=[b-a for a,b in zip(lower,upper)]
    error=max(abs(a-b*100) for a,b in zip(dimensions,meta["master"]["dimensions_m"]))
    if error>.5:raise RuntimeError("Imported full-scout dimensions differ: "+str(dimensions))
    report.update(passed=True,dimensions_cm=dimensions,max_dimension_error_cm=error,
        source_fbx_sha256=hashlib.sha256((asset/"unreal/scout_1_LOD0.fbx").read_bytes()).hexdigest(),physics=False)
    content=Path(unreal.Paths.project_content_dir())/"Campaign";content.mkdir(exist_ok=True)
    (content/"scout.json").write_text(json.dumps(report,indent=2)+"\n")
finally:
    (root/"test-results/campaign-scout-import.json").write_text(json.dumps(report,indent=2)+"\n")
