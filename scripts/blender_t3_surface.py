"""Run with Blender --background --python ... -- --surface ... --out ... .

Create static interchange files from the verified DEM/imagery package. This
does not author extra geometry or assert that an Unreal import has passed.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def dimensions(obj):
    points=[obj.matrix_world@Vector(corner) for corner in obj.bound_box]
    return [max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--surface',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=args.surface.resolve();out=args.out.resolve()
    if out.exists():raise ValueError('Choose a new Blender output directory')
    out.mkdir(parents=True);(out/'fbx').mkdir()
    manifest=json.loads((source/'manifest.json').read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    terrain=bpy.data.collections.new('COL_BXW_DERIVED_TERRAIN');scene.collection.children.link(terrain)
    objects=[];checks=[];materials={}
    for index,tile in enumerate(manifest['meshes']):
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.wm.obj_import(filepath=str(source/tile['visual_relative_path']),forward_axis='Y',up_axis='Z')
        selected=[o for o in bpy.context.selected_objects if o.type=='MESH']
        if len(selected)!=1:raise ValueError('Expected one mesh per terrain tile')
        obj=selected[0];obj.name='SM_BXW_'+tile['id']+'_LOD0'
        for collection in list(obj.users_collection):collection.objects.unlink(obj)
        terrain.objects.link(obj)
        if obj.data.validate(verbose=True):raise ValueError('Invalid imported terrain mesh')
        if len(obj.data.polygons)!=tile['triangles'] or len(obj.data.uv_layers)!=1:
            raise ValueError('Triangle/UV contract changed during import')
        if any(len(face.vertices)!=3 for face in obj.data.polygons):raise ValueError('Non-triangle terrain')
        expected=[tile['bounds_map_m'][2]-tile['bounds_map_m'][0],
                  tile['bounds_map_m'][3]-tile['bounds_map_m'][1],
                  tile['z_bounds_map_m'][1]-tile['z_bounds_map_m'][0]]
        actual=dimensions(obj)
        if max(abs(a-b) for a,b in zip(actual,expected))>.001:raise ValueError('OBJ scale or axes changed')
        for slot in obj.material_slots:
            key=slot.material.name.split('.')[0]
            if key in materials:slot.material=materials[key]
            else:materials[key]=slot.material
        fbx=out/'fbx'/(obj.name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
            global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
            axis_forward='-Y',axis_up='Z',use_mesh_modifiers=False,bake_anim=False,
            path_mode='RELATIVE',embed_textures=False)
        # A real re-import checks units and axis conventions on every tile.
        obj.select_set(False)
        bpy.ops.import_scene.fbx(filepath=str(fbx),use_anim=False)
        imported=[o for o in bpy.context.selected_objects if o.type=='MESH']
        if len(imported)!=1:raise ValueError('FBX roundtrip changed mesh count')
        difference=max(abs(a-b) for a,b in zip(dimensions(imported[0]),actual))
        if difference>.001:raise ValueError('FBX roundtrip scale error exceeds 1 mm')
        for duplicate in imported:bpy.data.objects.remove(duplicate,do_unlink=True)
        obj.location=tile['pose_map_m'][:3];objects.append(obj)
        checks.append({'id':tile['id'],'triangles':tile['triangles'],'dimensions_m':actual,
                       'fbx_roundtrip_max_dimension_error_m':difference,
                       'actor_pose_map_m':tile['pose_map_m'],'fbx':str(fbx.relative_to(out)),'passed':True})
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out/'BXW_surface.glb'),export_format='GLB',use_selection=True,
                              export_yup=True,export_animations=False)
    # Fixed technical illumination and camera; no invented surface features.
    center=Vector((0,0,sum(tile['pose_map_m'][2] for tile in manifest['meshes'])/len(manifest['meshes'])))
    camera_data=bpy.data.cameras.new('CAM_BXW_OVERVIEW');camera=bpy.data.objects.new('CAM_BXW_OVERVIEW',camera_data)
    scene.collection.objects.link(camera);scene.camera=camera
    camera.location=center+Vector((-650,-850,650));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.lens=38;camera_data.clip_end=10000
    light_data=bpy.data.lights.new('LGT_DIAGNOSTIC_SUN','SUN');light_data.energy=2
    light=bpy.data.objects.new('LGT_DIAGNOSTIC_SUN',light_data);scene.collection.objects.link(light)
    light.rotation_euler=(.4,-.5,-.4)
    scene.world=bpy.data.worlds.new('WORLD_DIAGNOSTIC');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.18,.18,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out/'BXW_surface_overview.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'BXW_surface.blend'))
    bpy.ops.render.render(write_still=True)
    result={'created_at_utc':datetime.now(timezone.utc).isoformat(),'blender':bpy.app.version_string,
            'status':'DERIVED','master_units':'metres; right handed ENU',
            'fbx_axes':{'forward':'-Y','up':'Z','unit_scale':1,'apply_scale_options':'FBX_SCALE_UNITS'},
            'glb':'Standard glTF metres/Y-up; file carries map-space tile transforms',
            'checks':checks,'passed':all(c['passed'] for c in checks),'unreal_import_verified':False,
            'limits':['Blender roundtrip is not an observed Unreal import.',
                      'Landscape holes outside measured mesh support remain open boundary edges.',
                      'No simplified convex terrain collision or artificial microgeometry was added.',
                      'Only fixed diagnostic lighting was used; baked orbital shadows remain in the texture.']}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
