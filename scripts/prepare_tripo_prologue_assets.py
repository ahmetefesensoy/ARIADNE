"""Preserve Tripo originals; prepare scale-checked prologue derivatives in Blender.

Run with Blender 5.2:
  blender --background --python scripts/prepare_tripo_prologue_assets.py -- <repo> [--asset prologue_turntable]

This is an original REDLINE packaging helper, not a previous application import.
No generator calls, source-file edits, NASA-data changes or physics assets are made.
Blender CLI is used because no Blender MCP connection is exposed in this session.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys
import traceback

import bpy
import bmesh
from mathutils import Matrix, Vector


ASSETS = {
    'prologue_turntable': {'span_m': .95, 'role': 'record-player visual console', 'budget': 79000},
    'prologue_lounge': {'span_m': 6., 'role': 'open-front lounge visual module', 'budget': 79000},
    'prologue_lander': {'span_m': 8., 'role': 'fictional landing-craft visual', 'budget': 79000},
    'prologue_airlock': {'span_m': 3., 'role': 'open-ended EVA airlock visual shell', 'budget': 79000},
    'prologue_command': {'span_m': 6., 'role': 'dedicated mission command interior', 'budget': 79000},
    'prologue_lab': {'span_m': 6., 'role': 'dedicated sample preparation laboratory interior', 'budget': 79000},
    'prologue_corridor': {'span_m': 15.6, 'role': 'dedicated habitat connecting corridor interior', 'budget': 79000},
}
SCHEMA = 'redline.tripo.prologue.asset.v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path, root):
    return str(Path(path).relative_to(root)).replace('\\', '/')


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def safe_name(value):
    return re.sub(r'[^A-Za-z0-9_]+', '_', value).strip('_') or 'Unnamed'


def bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        raise RuntimeError('No render mesh bounds')
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    if not all(math.isfinite(x) for p in (low, high) for x in p):
        raise RuntimeError('Non-finite mesh bounds')
    return low, high


def triangles(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0] if objects else None


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.


def pick_source(repo, asset_id, override=None):
    if override:
        p = Path(override).resolve()
        if not p.is_file() or p.suffix.lower() not in ('.glb', '.gltf'):
            raise RuntimeError('Source override must be an existing GLB/GLTF')
        return p
    folder = repo/'assets/incoming'/asset_id/'tripo'
    candidates = list(folder.rglob('*.glb'))
    # Prefer the completed primary download over a thumbnail or converter result.
    primary = [p for p in candidates if p.name.lower() in ('model.glb', 'textured_model.glb')]
    candidates = primary or candidates
    if not candidates:
        raise FileNotFoundError(f'Tripo model is not ready: {folder}')
    return max(candidates, key=lambda p: p.stat().st_size)


def original_images(objects, output):
    """Copy embedded/source bytes; never repaint or relabel their provenance."""
    used = {}
    for obj in objects:
        for material in obj.data.materials:
            if not material or not material.use_nodes:
                continue
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    used[node.image.as_pointer()] = node.image
    textures = []
    texture_by_image = {}
    for index, image in enumerate(used.values()):
        packed = image.packed_file
        original = Path(bpy.path.abspath(image.filepath)) if image.filepath else None
        if packed:
            data = bytes(packed.data)
        elif original and original.is_file():
            data = original.read_bytes()
        else:
            raise RuntimeError('Image has no original bytes: '+image.name)
        ext = '.png' if data.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if data[:3] == b'\xff\xd8\xff' else '.bin'
        if ext == '.bin':
            raise RuntimeError('Unsupported embedded image format: '+image.name)
        name = f'T_{index:02d}_{safe_name(image.name.rsplit(".", 1)[0])}{ext}'
        path = output/'textures'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        image.filepath = str(path)
        texture_by_image[image.as_pointer()] = 'textures/'+name
        textures.append({'path': 'textures/'+name, 'sha256': sha(path), 'bytes':len(data),
                         'source_image':image.name, 'size_px':list(image.size),
                         'colorspace':image.colorspace_settings.name, 'method':'original bytes copied'})
    return textures, texture_by_image


def socket_binding(socket, image_paths, seen=None):
    """Resolve the actual glTF Principled inputs, including packed channels."""
    if not socket.is_linked:
        value = socket.default_value
        return {'constant':list(value) if hasattr(value, '__len__') else float(value)}
    seen = seen or set()
    link = socket.links[0]
    node = link.from_node
    key = node.as_pointer()
    if key in seen:
        return {'unresolved':'cyclic node path'}
    seen.add(key)
    if node.type == 'TEX_IMAGE' and node.image:
        return {'path':image_paths[node.image.as_pointer()], 'image':node.image.name,
                'component':'A' if link.from_socket.name == 'Alpha' else 'RGB',
                'colorspace':node.image.colorspace_settings.name}
    if node.type in ('SEPRGB', 'SEPARATE_COLOR'):
        binding = socket_binding(node.inputs[0], image_paths, seen)
        binding['component'] = {'Red':'R','Green':'G','Blue':'B','R':'R','G':'G','B':'B'}.get(link.from_socket.name,link.from_socket.name)
        return binding
    if node.type == 'NORMAL_MAP':
        binding = socket_binding(node.inputs['Color'], image_paths, seen)
        binding.update(normal_convention='OpenGL', strength=float(node.inputs['Strength'].default_value))
        return binding
    # glTF may wrap a base color tint in a Multiply node. Keep that tint explicit
    # rather than silently claiming it is the unmodified image.
    if node.type == 'MIX' and len(node.inputs) > 7:
        linked = [s for s in node.inputs if s.is_linked]
        if len(linked) == 1:
            binding = socket_binding(linked[0], image_paths, seen)
            binding['node_note'] = 'glTF mix/tint path; review source defaults before reproducing in UE'
            return binding
    return {'unresolved':node.bl_idname, 'output':link.from_socket.name}


def materials(objects, image_paths, asset_id):
    unique = {}
    for obj in objects:
        for mat in obj.data.materials:
            if mat: unique[mat.as_pointer()] = mat
    output = {}
    for index, mat in enumerate(unique.values()):
        original_name = mat.name
        mat.name = f'MAT_{asset_id}_{index:02d}'
        entry = {'source_material_name':original_name, 'channels':{}, 'double_sided':not mat.use_backface_culling}
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'),None) if mat.use_nodes else None
        if not bsdf:
            entry['channels'] = {'Base Color':{'constant':list(mat.diffuse_color)},
                                 'Roughness':{'constant':float(mat.roughness)}, 'Metallic':{'constant':float(mat.metallic)}}
        else:
            for channel in ('Base Color','Roughness','Metallic','Normal'):
                entry['channels'][channel] = socket_binding(bsdf.inputs[channel],image_paths)
        output[mat.name] = entry
    return output


def mesh_audit(objects):
    result = []
    for obj in objects:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        result.append({'name':obj.name, 'vertices':len(obj.data.vertices), 'triangles':triangles(obj),
                       'material_slots':len(obj.data.materials), 'uv_layers':len(obj.data.uv_layers),
                       'boundary_edges':sum(e.is_boundary for e in bm.edges),
                       'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
                       'wire_edges':sum(e.is_wire for e in bm.edges),
                       'zero_area_faces':sum(f.calc_area() <= 1e-14 for f in bm.faces)})
        bm.free()
    return result


def bake_transform(objects, target_span):
    # glTF's nominal front is -Y after Blender import. Adopt +X forward by +90 Z.
    # Semantic front of generated art is checked visually rather than inferred
    # from a bounding box; that caveat remains in the manifest.
    rotation = Matrix.Rotation(math.pi/2,4,'Z')
    for obj in objects:
        obj.data = obj.data.copy()
        obj.data.transform(rotation @ obj.matrix_world)
        obj.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    low,high = bounds(objects)
    horizontal = max(high.x-low.x,high.y-low.y)
    if horizontal <= 1e-8:
        raise RuntimeError('Zero horizontal model span')
    scale = target_span/horizontal
    offset = Vector((-(high.x+low.x)/2,-(high.y+low.y)/2,-low.z))
    conversion = Matrix.Scale(scale,4) @ Matrix.Translation(offset)
    for obj in objects:
        obj.data.transform(conversion)
    bpy.context.view_layer.update()
    return scale, list(offset), list(low), list(high)


def decimate_to(objects, target):
    count = sum(triangles(o) for o in objects)
    if count <= target:
        return {'applied':False,'before':count,'after':count}
    ratio = max(.001,min(.999,target/count*.995))
    for obj in objects:
        if triangles(obj)<12:continue
        select([obj])
        modifier = obj.modifiers.new('DERIVED_BudgetReduction','DECIMATE')
        modifier.decimate_type = 'COLLAPSE'
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    after = sum(triangles(o) for o in objects)
    if after > target:
        raise RuntimeError(f'Derived triangle budget missed: {after}>{target}')
    return {'applied':True,'before':count,'after':after,'ratio':ratio,
            'note':'Source GLB retained; deterministic collapse only in derivative, UV layers retained'}


def remove_degenerate_geometry(objects):
    """Drop only numerically zero-area faces and unused edges in the derivative."""
    removed = {'faces':0,'wire_edges':0,'loose_vertices':0,'area_threshold_m2':1e-14}
    for obj in objects:
        bm = bmesh.new();bm.from_mesh(obj.data)
        faces = [f for f in bm.faces if f.calc_area() <= removed['area_threshold_m2']]
        removed['faces'] += len(faces)
        if faces:bmesh.ops.delete(bm,geom=faces,context='FACES_ONLY')
        edges = [e for e in bm.edges if e.is_wire]
        removed['wire_edges'] += len(edges)
        if edges:bmesh.ops.delete(bm,geom=edges,context='EDGES')
        vertices = [v for v in bm.verts if not v.link_edges]
        removed['loose_vertices'] += len(vertices)
        if vertices:bmesh.ops.delete(bm,geom=vertices,context='VERTS')
        bm.to_mesh(obj.data);bm.free();obj.data.update()
    return removed


def export_fbx(objects,path):
    select(objects)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
        global_scale=1.,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
        axis_forward='-Y',axis_up='Z',use_mesh_modifiers=False,bake_anim=False,
        mesh_smooth_type='FACE',path_mode='RELATIVE',embed_textures=False)


def roundtrip_fbx(objects,path):
    expected_low,expected_high = bounds(objects)
    expected = expected_high-expected_low
    select([])
    bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    imported = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    low,high = bounds(imported)
    actual = high-low
    error = max(abs(a-b) for a,b in zip(expected,actual))
    bounds_error = max(abs(a-b) for a,b in zip(list(expected_low)+list(expected_high),list(low)+list(high)))
    pivot_error = max(abs(low.z),abs((low.x+high.x)/2),abs((low.y+high.y)/2))
    texture_names = sorted({n.image.name for obj in imported for m in obj.data.materials if m and m.use_nodes
                            for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image})
    for obj in imported:bpy.data.objects.remove(obj,do_unlink=True)
    if error > 1e-5 or bounds_error > 1e-5:
        raise RuntimeError(f'FBX roundtrip units/pivot failed: error={error}, pivot={pivot_error}')
    return {'dimensions_m':list(actual),'dimension_error_m':error,'bounds_error_m':bounds_error,'bottom_center_offset_m':pivot_error,
            'texture_names_after_fbx_roundtrip':texture_names,'passed':True}


def preview(objects,path):
    scene = bpy.context.scene
    low,high = bounds(objects)
    center = (low+high)/2
    size = max(high-low)
    world = bpy.data.worlds.new('SCENARIO_PreviewWorld')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.15,.15,.15,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
    scene.world = world
    camera_data = bpy.data.cameras.new('QA_Camera')
    camera = bpy.data.objects.new('QA_Camera',camera_data)
    scene.collection.objects.link(camera)
    camera.location = center+Vector((2.8,-2.0,1.8))*size
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = size*1.5
    scene.camera = camera
    light_objects = []
    for index,(offset,power) in enumerate([((2,-1,3),900),((-2,-1,2),600),((1,2,3),800)]):
        data = bpy.data.lights.new('QA_Area_'+str(index),'AREA')
        data.energy = power*size*size
        data.shape = 'DISK';data.size = size*2
        obj = bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj)
        obj.location = center+Vector(offset)*size
        obj.rotation_euler = (center-obj.location).to_track_quat('-Z','Y').to_euler()
        light_objects.append(obj)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 512;scene.render.resolution_y = 512;scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG';scene.render.filepath = str(path)
    scene.render.film_transparent = False
    bpy.ops.render.render(write_still=True)
    for obj in light_objects+[camera]:bpy.data.objects.remove(obj,do_unlink=True)


def prepare(repo,asset_id,source_path,render):
    reset_scene()
    config = ASSETS[asset_id]
    output = repo/'data/engines/prologue-tripo-v1'/asset_id
    output.mkdir(parents=True,exist_ok=True)
    source_digest = sha(source_path)
    bpy.ops.import_scene.gltf(filepath=str(source_path))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not meshes:raise RuntimeError('Tripo model has no mesh')
    before = mesh_audit(meshes)
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH':bpy.data.objects.remove(obj,do_unlink=True)
    scale,offset,source_low,source_high = bake_transform(meshes,config['span_m'])
    portal_edit = None
    if asset_id=='prologue_airlock':
        # The generator supplied one open front and a closed rear leaf. Cut
        # only the derived rear portal so independent UE doors control passage.
        # Split faces first: UV interpolation is retained at the aperture edge.
        floor_z=.3093385696411133
        removed=0
        for obj in meshes:
            bm=bmesh.new();bm.from_mesh(obj.data)
            for point,normal in [((-.65,0,0),(1,0,0)),((.65,0,0),(1,0,0)),((0,0,floor_z-.03),(0,0,1)),((0,0,floor_z+2.17),(0,0,1)),((0,-.75,0),(0,1,0))]:
                bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=Vector(point),plane_no=Vector(normal),clear_inner=False,clear_outer=False)
            faces=[f for f in bm.faces if (lambda p: abs(p.x)<.65 and p.y<-.75 and floor_z-.03<p.z<floor_z+2.17)(f.calc_center_median())]
            removed+=len(faces)
            bmesh.ops.delete(bm,geom=faces,context='FACES_ONLY');bm.to_mesh(obj.data);bm.free();obj.data.update()
        portal_edit={'method':'UV-preserving plane splits and derived rear-leaf face removal','removed_faces':removed,'opening_width_m':1.3,'opening_height_m':2.2,'floor_anchor_m':floor_z,'raw_source_unchanged':True}
    if asset_id=='prologue_corridor':
        # Fit the generated inner passage, rather than compressing its outer
        # bounding box to human height. Author the four side portals at the
        # exact room/airlock connections; original download stays unchanged.
        floor_z=.3712329864501953;top=floor_z+5.0
        voids=[(-1.25,1.25,-7.2,7.2,floor_z+.02,top)]
        voids += [(-6.6,0,y-1.05,y+1.05,floor_z-.02,top) for y in (-6.,0.,6.)]
        voids += [(0,6.6,-.75,.75,floor_z-.02,top)]
        removed=0
        for obj in meshes:
            bm=bmesh.new();bm.from_mesh(obj.data)
            for x0,x1,y0,y1,z0,z1 in voids:
                for point,normal in [((x0,0,0),(1,0,0)),((x1,0,0),(1,0,0)),((0,y0,0),(0,1,0)),((0,y1,0),(0,1,0)),((0,0,z0),(0,0,1)),((0,0,z1),(0,0,1))]:
                    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=Vector(point),plane_no=Vector(normal),clear_inner=False,clear_outer=False)
                faces=[f for f in bm.faces if (lambda p:x0<p.x<x1 and y0<p.y<y1 and z0<p.z<z1)(f.calc_center_median())]
                removed+=len(faces);bmesh.ops.delete(bm,geom=faces,context='FACES_ONLY')
            bm.to_mesh(obj.data);bm.free();obj.data.update()
        portal_edit={'method':'UV-preserving portal/central-clearance cuts in SCENARIO derivative','removed_faces':removed,'portal_count':4,'raw_source_unchanged':True,'floor_anchor_m':floor_z}
    for index,obj in enumerate(meshes):
        obj.name = f'SM_{asset_id}_{index:02d}_LOD0'
        obj.data.name = obj.name+'_Mesh'
        obj.data.validate(verbose=False,clean_customdata=False)
        if not obj.data.vertices or not obj.data.polygons:raise RuntimeError('Empty mesh part '+obj.name)
    textures,image_paths = original_images(meshes,output)
    binding = materials(meshes,image_paths,asset_id)
    if len(binding)>8:raise RuntimeError('Material budget exceeded (>8), needs explicit atlas review')
    reduction = decimate_to(meshes,config['budget'])
    cleanup = remove_degenerate_geometry(meshes)
    # Decimation can remove an extremal vertex. Recenter and measure the final
    # derivative, rather than labelling the pre-decimation dimensions exact.
    final_low,final_high = bounds(meshes)
    final_scale = config['span_m']/max(final_high.x-final_low.x,final_high.y-final_low.y)
    final_offset = Vector((-(final_high.x+final_low.x)/2,-(final_high.y+final_low.y)/2,-final_low.z))
    correction = Matrix.Scale(final_scale,4) @ Matrix.Translation(final_offset)
    for obj in meshes:obj.data.transform(correction)
    bpy.context.view_layer.update()
    audit = mesh_audit(meshes)
    if any(item['wire_edges'] or item['zero_area_faces'] for item in audit):
        raise RuntimeError('Wire/zero-area geometry requires source-aware cleanup before export')
    if textures and any(item['uv_layers'] == 0 for item in audit):
        raise RuntimeError('Textured part has no UV coordinates')
    low,high = bounds(meshes)
    dimensions = high-low
    if abs(max(dimensions.x,dimensions.y)-config['span_m'])>1e-5:raise RuntimeError('Target scale changed during audit')
    brief = {'asset_id':asset_id,'purpose':config['role'],'platform':'PC/Unreal 5.8.4',
             'triangle_budget_LOD0':config['budget'],'target_horizontal_span_m':config['span_m'],
             'source_policy':'Keep original Tripo bytes unchanged; derivative art is SCENARIO, AI-generated',
             'collision':'Presentation only; do not import the visual mesh as Gazebo collision',
             'front_policy':'glTF nominal -Y adopted as +X; generated semantic front requires visual review',
             'review':'No claims about flight hardware, actual Mars interiors or album art'}
    write_json(output/'production_brief.json',brief)
    write_json(output/'material_bindings.json',binding)
    paths=[]
    main_fbx=output/f'SM_{asset_id}_LOD0.fbx'
    export_fbx(meshes,main_fbx)
    checked=roundtrip_fbx(meshes,main_fbx)
    paths.append({'kind':'FBX','lod':0,'file':main_fbx.name,'sha256':sha(main_fbx),'triangles':sum(triangles(o) for o in meshes),'roundtrip':checked})
    main_glb=output/f'SM_{asset_id}.glb'
    select(meshes)
    bpy.ops.export_scene.gltf(filepath=str(main_glb),export_format='GLB',use_selection=True,
                              export_yup=True,export_apply=True,export_animations=False,export_materials='EXPORT')
    paths.append({'kind':'GLB','lod':0,'file':main_glb.name,'sha256':sha(main_glb),'triangles':sum(triangles(o) for o in meshes)})
    # Keep a reusable source-preserving master before lower-detail derivatives.
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'derived.blend'))
    for level,fraction in ((1,.5),(2,.25)):
        copies=[]
        for obj in meshes:
            copy=obj.copy();copy.data=obj.data.copy();copy.name=obj.name.replace('LOD0','LOD'+str(level))
            bpy.context.scene.collection.objects.link(copy);copies.append(copy)
        decimate_to(copies,max(32,int(sum(triangles(o) for o in meshes)*fraction)))
        path=output/f'SM_{asset_id}_LOD{level}.fbx'
        export_fbx(copies,path)
        roundtrip=roundtrip_fbx(copies,path)
        paths.append({'kind':'FBX','lod':level,'file':path.name,'sha256':sha(path),'triangles':sum(triangles(o) for o in copies),'roundtrip':roundtrip})
        for obj in copies:bpy.data.objects.remove(obj,do_unlink=True)
    if render:
        preview(meshes,output/'preview.png')
    if sha(source_path)!=source_digest:raise RuntimeError('Original Tripo source changed during packaging')
    task_id=next((m.group(0) for p in source_path.parents for m in [re.search(r'[0-9a-f]{8}-[0-9a-f-]{27,}',p.name)] if m),None)
    result={'schema':SCHEMA,'asset_id':asset_id,'created_at_utc':datetime.now(timezone.utc).isoformat(),
            'status':'SCENARIO','ai_generated':True,'generator':'Tripo; supplied completed generation, no new calls here',
            'source_file':relative(source_path,repo),'source_sha256':source_digest,'source_modified':False,'task_id_from_path':task_id,
            'source_notices':'Tripo account/model terms apply; not CC0, not NASA archive; user authorized creation',
            'unit':'metre','axes':'+X adopted forward / +Y left / +Z up','handedness':'right',
            'origin':'bottom-center of render geometry','source_nominal_front':'-Y in Blender after glTF import',
            'semantic_front_verified':False,'semantic_front_note':'Visual orientation review is required; a box cannot prove which generated side is the front.',
            'normalization':{'rotation_about_z_deg':90,'uniform_scale':scale,'translation_before_scale_m':offset,'source_bounds_low':source_low,'source_bounds_high':source_high},
            'dimensions_m':list(dimensions),'triangle_count':sum(triangles(o) for o in meshes),'object_count':len(meshes),
            'material_count':len(binding),'textures':textures,'material_bindings':'material_bindings.json',
            'pre_export_audit':audit,'source_audit':before,'budget_reduction':reduction,'degenerate_cleanup':cleanup,
            'portal_edit':portal_edit,
            'post_decimation_normalization':{'uniform_scale':final_scale,'translation_m':list(final_offset)},
            'boundary_geometry_policy':'Open-front architectural/visual surface boundaries retained; no watertight collider claim',
            'exports':paths,'preview':'preview.png' if render else None,'unreal_import':'NOT_RUN by this script',
            'physics_authority':'No physics/control. Existing ROS/Gazebo authority unchanged.',
            'passed':True,'verdict':'SHIP_WITH_NOTES for engine import; semantic facing and final look need Unreal review'}
    # mathutils.Vector values are materialized for a portable JSON manifest.
    result['normalization']['source_bounds_low']=list(source_low)
    result['normalization']['source_bounds_high']=list(source_high)
    write_json(output/'manifest.json',result)
    (output/'SOURCE.md').write_text(
        '# '+asset_id+' — Tripo-derived presentation art\n\n'
        'This visual was generated by Tripo at the user’s request. Its original downloaded bytes\n'
        'remain under assets/incoming/'+asset_id+'/tripo. Source SHA-256 and generation task path\n'
        'are recorded in manifest.json. Tripo account/model terms continue to apply; no CC0\n'
        'or NASA archive licence is asserted. The asset is SCENARIO / AI-generated art, not\n'
        'measured engineering hardware, a NASA habitat interior or a rover-control input.\n\n'
        'Packaging code authored for REDLINE uses Blender CLI because no Blender MCP connection\n'
        'is exposed in this session. Textures were copied from original bytes. Scale, rotation,\n'
        'bottom pivot and any decimation are explicit derivative transformations. Physics and\n'
        'control remain outside these files. Any Chet Baker lettering/cover is added separately;\n'
        'this package does not contain music or claim rights to third-party recordings.\n',encoding='utf-8')
    return result


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    parser.add_argument('--asset',action='append',choices=list(ASSETS))
    parser.add_argument('--source',type=Path,help='Single-asset source override')
    parser.add_argument('--no-render',action='store_true')
    parsed=parser.parse_args(args)
    repo=parsed.repo.resolve()
    names=parsed.asset or list(ASSETS)
    if parsed.source and len(names)!=1:raise RuntimeError('--source needs exactly one --asset')
    report={'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'SCENARIO','assets':[],'passed':False}
    try:
        for name in names:
            path=pick_source(repo,name,parsed.source)
            result=prepare(repo,name,path,not parsed.no_render)
            report['assets'].append({'asset_id':name,'manifest':f'data/engines/prologue-tripo-v1/{name}/manifest.json',
                                     'dimensions_m':result['dimensions_m'],'triangles':result['triangle_count'],
                                     'source_sha256':result['source_sha256'],'passed':result['passed']})
            print('REDLINE_TRIPO_ASSET '+json.dumps(report['assets'][-1]),flush=True)
        report['passed']=all(a['passed'] for a in report['assets']) and len(report['assets'])==len(names)
    except Exception as error:
        report.update(error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        (repo/'test-results').mkdir(exist_ok=True)
        write_json(repo/'test-results/tripo-prologue-pipeline.json',report)
        print('REDLINE_TRIPO_PIPELINE '+json.dumps(report),flush=True)


if __name__=='__main__':main()
