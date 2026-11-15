"""Build local visual asset deliverables with Blender, without application edits.

Usage: blender --background --disable-autoexec --python build_package.py -- <ids>
Original files are never overwritten. Engine acceptance is always recorded as
pending until an actual Unreal/Gazebo import is observed.
"""
from __future__ import annotations
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from preview import bounds, views

SPECS={
 "astronaut": {"source":"animated", "height":1.85,"lod0":95000,"gazebo":8000,"texture":2048},
 "rover_1": {"source":"nasa", "lod0":150000,"gazebo":25000,"texture":2048},
 "scout_1": {"source":"drone", "longest":1.2,"lod0":60000,"gazebo":12000,"texture":2048},
 "pr_1": {"source":"source.glb", "longest":5.91,"lod0":150000,"gazebo":30000,"texture":2048},
 "habitat": {"source":"source.glb", "longest":8.0,"lod0":100000,"gazebo":10000,"texture":2048},
 "science_station": {"source":"source.glb", "height":1.25,"lod0":30000,"gazebo":6500,"texture":1024},
 "tool_apxs": {"source":"source.glb","longest":0.18,"lod0":15000,"gazebo":2000,"texture":1024},
 "tool_libs": {"source":"source.glb","longest":0.32,"lod0":15000,"gazebo":3000,"texture":1024},
 "tool_drill": {"source":"source.glb","height":0.65,"lod0":15000,"gazebo":3000,"texture":1024},
 "tool_neutron": {"source":"source.glb","longest":0.30,"lod0":15000,"gazebo":2000,"texture":1024},
 "tool_multispectral": {"source":"source.glb","longest":0.24,"lod0":15000,"gazebo":3000,"texture":1024},
 "sample_tube": {"source":"source.stl","height":0.15,"lod0":7000,"gazebo":1500,"texture":1024},
 "sample_case": {"source":"container","longest":0.45,"lod0":8000,"gazebo":2000,"texture":1024},
 "rock_07": {"source":"source.gltf","longest":0.45,"lod0":4500,"gazebo":800,"texture":1024},
 "rock_09": {"source":"source.gltf","longest":0.25,"lod0":4500,"gazebo":800,"texture":1024},
}


def clean(name):
    return re.sub(r"[^A-Za-z0-9_]","_",name)


def select(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.hide_set(False);o.select_set(True)
    if objects:bpy.context.view_layer.objects.active=objects[0]


def triangles(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


def new_collection(name):
    c=bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def move(o,c):
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o)


def decimate(o,ratio):
    if ratio>=0.999 or triangles(o)<24:return
    select([o])
    m=o.modifiers.new("Visual_LOD_reduction","DECIMATE")
    m.ratio=max(0.001,ratio)
    # Apply before the armature; preserve interpolated vertex-group weights.
    while o.modifiers.find(m.name)>0:
        bpy.ops.object.modifier_move_up(modifier=m.name)
    bpy.ops.object.modifier_apply(modifier=m.name)


def load_nasa(spec):
    path=ROOT/"incoming/curiosity_reference/source.blend"
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):
        dst.objects=src.objects
    for o in dst.objects:
        if o and not o.users_collection:bpy.context.scene.collection.objects.link(o)
    # The native file is saved at frame 180 (deployed mast/arm/suspension).
    # Frame 1 is the source's unfolding animation, not a neutral rover pose.
    bpy.context.scene.frame_set(180)
    bpy.context.view_layer.update()
    chosen=set(spec.get("select",[]))
    objects=list(bpy.context.scene.objects)
    matrices={o:o.matrix_world.copy() for o in objects}
    parents={o:o.parent.name if o.parent else '' for o in objects}
    # Bake the supplied pose, not the source's old animation/constraints.
    for o in objects:
        o.parent=None;o.animation_data_clear()
        for c in list(o.constraints):o.constraints.remove(c)
        o.matrix_world=matrices[o]
    keep=[]
    for o in objects:
        if o.type!="MESH" or (chosen and o.name not in chosen) or "shadow" in o.name.lower() or o.name.endswith("_p"):
            bpy.data.objects.remove(o,do_unlink=True)
        else:
            o.data=o.data.copy()
            o.hide_render=False;o.hide_viewport=False;o.hide_set(False)
            o["source_object"]=o.name
            o["source_parent"]=parents[o]
            o["source_pivot"]=list(matrices[o].translation)
            keep.append(o)
    kept_names={o.name for o in keep}
    for o in keep:
        parent=parents.get(o,'')
        visited=set()
        name_to_parent={name.name:parents[name] for name in parents if name in keep}
        # The source hierarchy is recorded even when helper pivots are removed.
        if parent not in kept_names:parent=''
        o['source_parent']=parent
    return keep,str(path.relative_to(ROOT))


def separate_selected_faces(o,indices,name):
    if not indices:return []
    select([o]);bpy.context.scene.tool_settings.mesh_select_mode=(False,False,True)
    for v in o.data.vertices:v.select=False
    for e in o.data.edges:e.select=False
    wanted=set(indices)
    for p in o.data.polygons:p.select=p.index in wanted
    before=set(bpy.context.scene.objects)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.separate(type='SELECTED');bpy.ops.object.mode_set(mode='OBJECT')
    parts=list(set(bpy.context.scene.objects)-before)
    for part in parts:part.name=name
    return parts


def tube_parts(o):
    # A presentation split of the printable NASA model; this is a scenario cap,
    # not a claim about the actual flight sample-tube sealing mechanism.
    cut=4.05
    upper=o.copy();upper.data=o.data.copy();bpy.context.scene.collection.objects.link(upper)
    for obj,above in ((o,False),(upper,True)):
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,cut),plane_no=(0,0,1),clear_inner=above,clear_outer=not above,dist=0.00001)
        edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<0.0001 for v in e.verts)]
        if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
        bm.to_mesh(obj.data);bm.free();obj.data.update()
    o.name='tube';upper.name='cap'
    mat=bpy.data.materials.new('MAT_Scenario_Titanium');mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(0.52,0.55,0.58,1);shader.inputs['Metallic'].default_value=0.8;shader.inputs['Roughness'].default_value=0.38
    for obj in (o,upper):obj.data.materials.clear();obj.data.materials.append(mat)
    return [o,upper]


def split_by_components(o, classifier):
    """Weld coincident source vertices, then group whole connected components.

    UVs remain on face corners. No wheel or door is cut across a triangle.
    """
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00001)
    unseen=set(bm.verts);groups=[]
    while unseen:
        seed=unseen.pop();verts=[seed];todo=[seed]
        while todo:
            v=todo.pop()
            for e in v.link_edges:
                nxt=e.other_vert(v)
                if nxt in unseen:unseen.remove(nxt);todo.append(nxt);verts.append(nxt)
        points=[o.matrix_world@v.co for v in verts]
        lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
        hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
        groups.append((classifier((lo+hi)*0.5,hi-lo),set(verts)))
    labels={v:label for label,vs in groups for v in vs}
    bm.faces.ensure_lookup_table();bm.faces.index_update()
    face_labels=[labels[f.verts[0]] for f in bm.faces]
    bm.to_mesh(o.data);bm.free()
    # select + separate preserves Blender's UV and material data without a rebake.
    by_label=defaultdict(list)
    for i,label in enumerate(face_labels):by_label[label].append(i)
    objects=[]
    remaining=o
    for label,indices in by_label.items():
        if label=="body":continue
        select([remaining])
        for p in remaining.data.polygons:p.select=False
        # Face indices remain stable until the first separation; use a face integer
        # attribute to retain labels through every subsequent separation.
    attr=o.data.attributes.new(name="component_label",type="INT",domain="FACE")
    label_ids={label:i for i,label in enumerate(by_label)}
    attr.data.foreach_set("value",[label_ids[x] for x in face_labels])
    for label,li in label_ids.items():
        if label=="body":continue
        select([o])
        bpy.context.scene.tool_settings.mesh_select_mode=(False,False,True)
        a=o.data.attributes["component_label"]
        for v in o.data.vertices:v.select=False
        for e in o.data.edges:e.select=False
        for p in o.data.polygons:p.select=(a.data[p.index].value==li)
        if not any(p.select for p in o.data.polygons):continue
        before=set(bpy.context.scene.objects)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.separate(type="SELECTED")
        bpy.ops.object.mode_set(mode="OBJECT")
        new=list(set(bpy.context.scene.objects)-before)
        for part in new:part.name=label;objects.append(part)
    o.name="body"
    if len(o.data.polygons):objects.append(o)
    else:bpy.data.objects.remove(o,do_unlink=True)
    if len([x for x in objects if x.name.startswith('wheel')])!=12:
        raise ValueError('SEV wheel separation did not preserve twelve wheel groups')
    return objects


def sev_classifier(center,size):
    # Source SEV has six bogies and two wheels per bogie: 12 wheels.
    for side in (-1,1):
        for axle,y in enumerate((-0.832,0.870,2.570)):
            for twin,x in enumerate((1.493,1.909)):
                if abs(center.x-side*x)<0.16 and abs(center.y-y)<0.4 and abs(center.z+1.86)<0.32 and size.x<0.34 and size.y<0.82 and size.z<0.82:
                    return f"wheel_{'L' if side>0 else 'R'}_{axle+1}_{twin+1}"
    # The two large circular side hatches are disconnected closed components.
    if abs(abs(center.x)-1.75)<0.15 and abs(center.y)<0.15 and abs(center.z)<0.15 and 1.3<size.y<1.8 and size.x<0.18:
        return "door_"+("L" if center.x>0 else "R")
    return "body"


def load_drone():
    reference=ROOT/"incoming/scout_1/processing/segmentation_input.glb"
    bpy.ops.import_scene.gltf(filepath=str(reference))
    source=next(o for o in bpy.context.scene.objects if o.type=="MESH")
    # Source UVs/materials are retained on the server's geometrically identical
    # split pieces, avoiding hundreds of low-resolution generated materials.
    source.name="UV_reference"
    path=next((ROOT/"incoming/scout_1/segmented").rglob("model.glb"))
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    parts=[o for o in set(bpy.context.scene.objects)-before if o.type=="MESH"]
    normalize_scale=0.9990294467834756
    for o in parts:
        o.location/=normalize_scale
        o.data.transform(Matrix.Scale(1/normalize_scale,4))
    bpy.context.view_layer.update()
    groups=defaultdict(list)
    rotor_hubs=[(-0.28,-0.322,0.18),(-0.343,0.308,0.16),(0.299,-0.319,0.055),(0.35,0.335,0.065)]
    for o in parts:
        lo,hi=bounds([o]);center=(lo+hi)*0.5;size=hi-lo
        label="body"
        for i,(x,y,z) in enumerate(rotor_hubs):
            if abs(center.x-x)<0.19 and abs(center.y-y)<0.19 and lo.z>z-0.032 and size.z<0.065:
                label=f"rotor_{i+1}";break
        groups[label].append(o)
    objects=[]
    for label,items in groups.items():
        select(items)
        bpy.ops.object.join()
        o=bpy.context.object;o.name=label;objects.append(o)
        select([o])
        mod=o.modifiers.new("Restore_original_UV","DATA_TRANSFER")
        mod.object=source;mod.use_loop_data=True;mod.data_types_loops={'UV'};mod.loop_mapping='POLYINTERP_NEAREST'
        bpy.ops.object.datalayout_transfer(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        o.data.materials.clear()
        for m in source.data.materials:o.data.materials.append(m)
        for p in o.data.polygons:p.material_index=0
        if label.startswith("rotor"):
            o["suggested_source_pivot"]=rotor_hubs[int(label[-1])-1]
    bpy.data.objects.remove(source,do_unlink=True)
    return objects,str(path.relative_to(ROOT))


def material_atlas(asset_id,objects):
    folder=ROOT/"incoming"/asset_id
    data=json.loads((folder/"atlas.json").read_text())
    mat=bpy.data.materials.new("MAT_"+asset_id+"_Atlas");mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links;bsdf=n.get("Principled BSDF")
    nodes={}
    for channel in ("BaseColor","ORM","NormalGL"):
        node=n.new("ShaderNodeTexImage")
        node.image=bpy.data.images.load(str(folder/"textures"/f"{asset_id}_{channel}.png"))
        if channel!="BaseColor":node.image.colorspace_settings.name="Non-Color"
        nodes[channel]=node
    l.new(nodes["BaseColor"].outputs['Color'],bsdf.inputs['Base Color'])
    sep=n.new("ShaderNodeSeparateColor");l.new(nodes['ORM'].outputs['Color'],sep.inputs['Color'])
    l.new(sep.outputs['Green'],bsdf.inputs['Roughness']);l.new(sep.outputs['Blue'],bsdf.inputs['Metallic'])
    normal=n.new("ShaderNodeNormalMap");l.new(nodes['NormalGL'].outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
    for o in list(objects):
        tile=data['tiles'].get(o.name)
        if tile is None:
            objects.remove(o);bpy.data.objects.remove(o,do_unlink=True);continue
        for uv in o.data.uv_layers.active.data:
            uv.uv=(tile['u']+uv.uv.x*tile['scale'],tile['v']+uv.uv.y*tile['scale'])
        o.data.materials.clear();o.data.materials.append(mat)
        for p in o.data.polygons:p.material_index=0


def nasa_materials(objects):
    # Four source diffuse sheets become a single 2K sheet. The source only has
    # diffuse/AO maps; no measured roughness or normal maps are invented.
    atlas=bpy.data.images.new("NASA_Curiosity_BaseColor",2048,2048,alpha=True)
    canvas=np.ones((2048,2048,4),dtype=np.float32)
    for i in range(4):
        img=bpy.data.images.get(f"tex_0{i+1}.png")
        if img and img.size[0]:
            arr=np.empty(1024*1024*4,dtype=np.float32);img.pixels.foreach_get(arr)
            row,col=divmod(i,2);canvas[row*1024:(row+1)*1024,col*1024:(col+1)*1024]=arr.reshape(1024,1024,4)
    atlas.pixels.foreach_set(canvas.ravel())
    mat=bpy.data.materials.new("MAT_NASA_Curiosity_Atlas");mat.use_nodes=True
    node=mat.node_tree.nodes.new("ShaderNodeTexImage");node.image=atlas
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    ao=bpy.data.materials.get('parts_AO')
    if ao:ao.name="MAT_NASA_parts_AO"
    white=bpy.data.materials.new("MAT_NASA_solid");white.diffuse_color=(0.65,0.65,0.65,1);white.use_nodes=True
    gold=bpy.data.materials.new("MAT_NASA_gold");gold.use_nodes=True
    gold.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(0.6,0.36,0.08,1)
    gold.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=0.8
    for o in objects:
        old=list(o.data.materials)
        o.data.materials.clear()
        for m in (mat,ao or white,white,gold):o.data.materials.append(m)
        for p in o.data.polygons:
            source=old[p.material_index] if p.material_index<len(old) else None
            name=source.name if source else ''
            match=re.match(r'tex_0([1-4])',name)
            if match:
                i=int(match.group(1))-1;row,col=divmod(i,2)
                if o.data.uv_layers.active:
                    for li in p.loop_indices:
                        uv=o.data.uv_layers.active.data[li].uv
                        uv.x=(uv.x+col)/2;uv.y=(uv.y+row)/2
                p.material_index=0
            else:p.material_index=1 if 'parts_AO' in name else 3 if 'foil_gold' in name else 2


def save_textures(objects,folder,max_size):
    folder.mkdir(exist_ok=True)
    mats={m for o in objects for m in o.data.materials if m}
    images={n.image for m in mats if m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.size[0]}
    results=[]
    for index,img in enumerate(sorted(images,key=lambda x:x.name)):
        if max(img.size)>max_size:
            ratio=max_size/max(img.size);img.scale(max(1,round(img.size[0]*ratio)),max(1,round(img.size[1]*ratio)))
        path=folder/(clean(img.name.rsplit('.',1)[0])+'.png')
        img.file_format='PNG';img.filepath_raw=str(path);img.save();img.pack()
        results.append({'name':img.name,'path':'textures/'+path.name,'width':img.size[0],'height':img.size[1],'colorspace':img.colorspace_settings.name})
    return results


def bake_static(objects,transform,asset_id):
    originals={o:o.name for o in objects}
    matrices={o:transform@o.matrix_world for o in objects}
    for o in objects:
        o.data=o.data.copy()
        o.parent=None;o.animation_data_clear()
        for m in list(o.modifiers):
            if m.type=='ARMATURE':o.modifiers.remove(m)
        o.data.transform(matrices[o])
        o.matrix_world=Matrix.Identity(4)
        o.data.update()
    bpy.context.view_layer.update()
    records=[]
    for o in objects:
        lo,hi=bounds([o]);pivot=(lo+hi)*0.5
        source=originals[o]
        if 'source_pivot' in o:pivot=transform@Vector(o['source_pivot'])
        if 'door' in source.lower():pivot.y=hi.y;pivot.z=lo.z
        if "antenna" in source.lower():pivot.z=lo.z
        if asset_id=='science_station':
            idx=int(source.rsplit('_',1)[-1])
            source=({0:'body',2:'leg_1',3:'leg_2',5:'leg_3',6:'leg_4',9:'antenna',4:'sensor_head'}.get(idx,f'panel_{idx}'))
            if 'leg' in source:pivot.z=hi.z
        if asset_id=='tool_drill':
            idx=int(source.rsplit('_',1)[-1])
            source={0:'motor_housing',1:'feed_carriage',2:'gearbox',3:'bit',6:'bit_collar'}.get(idx,f'fixture_{idx}')
            if source=='bit':pivot.z=hi.z
        if 'suggested_source_pivot' in o:
            pivot=transform@Vector(o['suggested_source_pivot'])
        o.data.transform(Matrix.Translation(-pivot));o.location=pivot
        o.name='SM_'+asset_id+'_'+clean(source)+'_LOD0'
        o['source_name']=originals[o]
        axis=(0,1,0) if 'wheel' in source else (0,0,1)
        records.append({'name':o.name,'source_name':originals[o],'source_parent':o.get('source_parent',''),'pivot_m':list(pivot),'suggested_axis':axis if any(k in source for k in ('wheel','rotor','leg','antenna','arm','mast','door')) else None,'joint_limits':None,'physics_parameters':None})
    # Keep assembled part transforms explicit and independent. Source parent names
    # are metadata for the future ROS presentation adapter, not an implicit second
    # robot joint hierarchy. This also avoids shifting children when pivots change.
    return records


def collision_box(o,collection):
    lo,hi=bounds([o]);size=hi-lo
    if min(size)<0.005:return None
    bpy.ops.mesh.primitive_cube_add(size=1,location=(lo+hi)*0.5)
    obj=bpy.context.object;obj.dimensions=size
    select([obj]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    # UCX object shares its corresponding visual mesh pivot.
    pivot=o.matrix_world.translation.copy()
    world=obj.matrix_world.copy();obj.data.transform(Matrix.Translation(-pivot)@world);obj.matrix_world=Matrix.Translation(pivot)
    obj.name='UCX_'+o.name+'_00';move(obj,collection)
    return obj


def character_capsule(collection):
    radius=0.28;height=1.85
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=radius)
    obj=bpy.context.object
    half=height*0.5-radius
    for v in obj.data.vertices:
        v.co.z+=half if v.co.z>=0 else -half
        v.co.z+=height*0.5
    obj.name='UCX_SK_Astronaut_LOD0_00';move(obj,collection)
    return obj


def write_obj(path,objects,local=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    mat_set={m for o in objects for m in o.data.materials if m}
    mtl=path.with_suffix('.mtl')
    with mtl.open('w',encoding='utf-8') as f:
        for m in sorted(mat_set,key=lambda v:v.name):
            f.write(f'newmtl {clean(m.name)}\nKd 0.8 0.8 0.8\nNs 16\n')
            node=next((n for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.colorspace_settings.name=='sRGB'),None) if m.use_nodes else None
            if node:
                import os
                rel=Path(bpy.path.abspath(node.image.filepath)).resolve()
                f.write('map_Kd '+Path(os.path.relpath(rel,path.parent)).as_posix()+'\n')
    offset=0;uv_offset=0;normal_offset=0
    with path.open('w',encoding='utf-8') as f:
        f.write('# REDLINE visual derivative: metres, right-handed +X/+Y/+Z\nmtllib '+mtl.name+'\n')
        for o in objects:
            mesh=o.data;mesh.calc_loop_triangles();matrix=Matrix.Identity(4) if local else o.matrix_world
            f.write('o '+o.name+'\n')
            for v in mesh.vertices:
                p=matrix@v.co;f.write(f'v {p.x:.9g} {p.y:.9g} {p.z:.9g}\n')
            uv=mesh.uv_layers.active
            for loop in mesh.loops:
                u,v=uv.data[loop.index].uv if uv else (0,0);f.write(f'vt {u:.9g} {v:.9g}\n')
            normals=mesh.corner_normals
            for i in range(len(mesh.loops)):
                n=matrix.to_3x3()@normals[i].vector;n.normalize();f.write(f'vn {n.x:.9g} {n.y:.9g} {n.z:.9g}\n')
            last=None
            for tri in mesh.loop_triangles:
                mi=mesh.polygons[tri.polygon_index].material_index
                m=mesh.materials[mi] if mi<len(mesh.materials) else None
                if m and m!=last:f.write('usemtl '+clean(m.name)+'\n');last=m
                inds=[f'{vi+1+offset}/{li+1+uv_offset}/{li+1+normal_offset}' for vi,li in zip(tri.vertices,tri.loops)]
                f.write('f '+' '.join(inds)+'\n')
            offset+=len(mesh.vertices);uv_offset+=len(mesh.loops);normal_offset+=len(mesh.loops)


def clone_lod(objects,collection,label,ratio):
    copies=[]
    for o in objects:
        dup=o.copy();dup.data=o.data.copy();collection.objects.link(dup)
        dup.parent=None;dup.matrix_world=o.matrix_world.copy();dup.name=o.name.replace('_LOD0','_'+label)
        dup.animation_data_clear()
        for m in list(dup.modifiers):
            if m.type=='ARMATURE':dup.modifiers.remove(m)
        decimate(dup,ratio);copies.append(dup)
    return copies


def audit(objects):
    meshes=[]
    for o in objects:
        bm=bmesh.new();bm.from_mesh(o.data)
        non_manifold=sum(not e.is_manifold for e in bm.edges);bm.free()
        meshes.append({'name':o.name,'triangles':triangles(o),'vertices':len(o.data.vertices),'uv_layers':len(o.data.uv_layers),'non_manifold_edges':non_manifold})
    return {'triangles':sum(m['triangles'] for m in meshes),'materials':len({m for o in objects for m in o.data.materials if m}),'parts':meshes}


def export_fbx(path,objects,animate=False):
    select(objects)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE','EMPTY'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,add_leaf_bones=False,primary_bone_axis='Y',secondary_bone_axis='X',bake_anim=animate,bake_anim_use_nla_strips=animate,bake_anim_use_all_actions=animate,path_mode='COPY',embed_textures=False)


def build(aid):
    spec=SPECS[aid];folder=ROOT/'incoming'/aid;folder.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    spec_source=spec['source']
    armatures=[]
    if spec_source=='nasa':objects,source=load_nasa(spec);nasa_materials(objects)
    elif spec_source=='drone':objects,source=load_drone()
    else:
        source=next((ROOT/'incoming/astronaut/animations').rglob('model.glb')) if spec_source=='animated' else ROOT/'incoming/industrial_pastic_container/source.gltf' if spec_source=='container' else folder/spec_source
        if source.suffix=='.stl':bpy.ops.wm.stl_import(filepath=str(source))
        else:bpy.ops.import_scene.gltf(filepath=str(source))
        source=str(source.relative_to(ROOT))
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
        if aid=='astronaut':
            armatures=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
            for arm in armatures:
                for b in arm.pose.bones:b.custom_shape=None
                arm.data.pose_position='REST'
            for o in list(objects):
                if not any(m.type=='ARMATURE' for m in o.modifiers):objects.remove(o);bpy.data.objects.remove(o,do_unlink=True)
        if aid in ('science_station','tool_drill'):material_atlas(aid,objects)
        if aid=='pr_1':objects=split_by_components(objects[0],sev_classifier)
        if aid=='sample_tube':objects=tube_parts(objects[0])
        if aid=='habitat':
            o=objects[0];lo,hi=bounds([o]);ids=[]
            for p in o.data.polygons:
                points=[o.matrix_world@o.data.vertices[i].co for i in p.vertices]
                if min(v.x for v in points)>hi.x-10:ids.append(p.index)
            objects+=separate_selected_faces(o,ids,'door')
    bpy.context.view_layer.update()
    before=audit(objects)
    low,high=bounds(objects);size=high-low
    scale=spec.get('height',size.z)/size.z if 'height' in spec else spec.get('longest',max(size))/max(size)
    angle=-math.pi/2 if aid=='astronaut' else 0 if aid.startswith('tool_') or aid in ('scout_1','habitat') else math.pi/2
    rotate=Matrix.Rotation(angle,4,'Z')
    transformed=[rotate@Vector(p) for o in objects for p in [o.matrix_world@Vector(v) for v in o.bound_box]]
    lo=Vector(tuple(min(p[i] for p in transformed) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in transformed) for i in range(3)))
    offset=Vector((-(lo.x+hi.x)*0.5,-(lo.y+hi.y)*0.5,-lo.z))*scale
    transform=Matrix.Translation(offset)@Matrix.Scale(scale,4)@rotate
    if armatures:
        root=bpy.data.objects.new('ROOT_'+aid,None);bpy.context.scene.collection.objects.link(root)
        for o in list(bpy.context.scene.objects):
            if o!=root and o.parent is None:o.parent=root
        root.matrix_world=transform
        for o in objects:o.name='SK_Astronaut_LOD0'
        records=[{'name':objects[0].name,'pivot_m':[0,0,0],'suggested_axis':None,'source_name':'Tripo Unreal biped skin'}]
        for o in objects:decimate(o,spec['lod0']/before['triangles'])
        for o in objects:
            select([o])
            bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL',limit=4)
            bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',lock_active=False)
    else:
        records=bake_static(objects,transform,aid)
        total=sum(triangles(o) for o in objects)
        for o in objects:decimate(o,min(1,spec['lod0']/total))
    c0=new_collection('COL_'+aid+'_LOD0')
    for o in objects+armatures:move(o,c0)
    bpy.context.view_layer.update()
    textures=save_textures(objects,folder/'textures',spec['texture'])
    lod0=audit(objects)
    paths={}
    for name in ('unreal','gazebo','preview'):(folder/name).mkdir(exist_ok=True)
    collisions=[];cc=new_collection('COL_Collision_'+aid)
    if aid=='astronaut':collisions.append(character_capsule(cc))
    for o in ([] if aid=='astronaut' else objects):
        name=o.get('source_name',o.name).lower()
        include=len(objects)<5 or any(s in name for s in ('wheel','rotor','body','chassis','arm_0','mast_0','tripo_part_0','leg_'))
        if include:
            col=collision_box(o,cc)
            if col:collisions.append(col)
    # Separate visual LODs; no automatic LOD selection is claimed.
    lods={}
    for level,ratio in ((1,0.5),(2,0.25)):
        c=new_collection('COL_'+aid+'_LOD'+str(level))
        # Skeletal LODs retain the armature modifier and skin weights.
        if armatures:
            copies=[]
            for o in objects:
                dup=o.copy();dup.data=o.data.copy();c.objects.link(dup);dup.name=o.name.replace('LOD0','LOD'+str(level));decimate(dup,ratio);copies.append(dup)
        else:copies=clone_lod(objects,c,'LOD'+str(level),ratio)
        lods[level]=copies
    gaz_c=new_collection('COL_Gazebo_'+aid)
    gaz=clone_lod(objects,gaz_c,'Gazebo',min(1,spec['gazebo']/lod0['triangles']))
    gaz_audit=audit(gaz)
    for o in gaz+collisions+[x for arr in lods.values() for x in arr]:o.hide_render=True
    # FBX outputs have separate collision meshes and local part pivots.
    for a in armatures:a.data.pose_position='POSE'
    path=folder/'unreal'/f'{aid}_LOD0.fbx'
    export_fbx(path,objects+armatures+collisions,animate=bool(armatures));paths['unreal_lod0']=str(path.relative_to(folder))
    for level,copies in lods.items():
        path=folder/'unreal'/f'{aid}_LOD{level}.fbx'
        export_fbx(path,copies+armatures,animate=False)
    select(objects+armatures)
    bpy.ops.export_scene.gltf(filepath=str(folder/'presentation.glb'),export_format='GLB',use_selection=True,export_animations=bool(armatures),export_def_bones=False)
    for a in armatures:a.data.pose_position='REST'
    write_obj(folder/'gazebo/assembly.obj',gaz)
    for o in gaz:write_obj(folder/'gazebo/parts'/f'{o.name}.obj',[o],local=True)
    write_obj(folder/'gazebo/collision.obj',collisions)
    sdf=f'''<?xml version="1.0"?>
<sdf version="1.10"><model name="{aid}_visual_preview"><static>true</static><link name="visual"><visual name="visual"><geometry><mesh><uri>assembly.obj</uri></mesh></geometry></visual></link></model></sdf>
'''
    (folder/'gazebo/visual.sdf').write_text(sdf,encoding='utf-8')
    # No inertia, joint limits, sensor frames, controllers or robot code is inferred.
    for o in collisions+[x for arr in lods.values() for x in arr]+gaz:o.hide_set(True)
    if armatures:
        for a in armatures:a.data.pose_position='REST'
    metadata={'asset_id':aid,'prepared_utc':datetime.now(timezone.utc).isoformat(),'blender_version':bpy.app.version_string,'source':source,'provenance':{'status':'SCENARIO','note':'Visual derivative; source library art is not an archive measurement. Source scale and placement are scenario choices.'},'master':{'unit':'metre','axes':'+X forward/+Y left/+Z up','handedness':'right','source_to_master_matrix':[list(row) for row in transform],'uniform_scale':scale,'scale_basis':'SCENARIO visual sizing; not a measured robot dimension','dimensions_m':list(bounds(objects)[1]-bounds(objects)[0])},'parts':records,'source_audit':before,'lod0':lod0,'lods':{str(k):audit(v) for k,v in lods.items()},'gazebo':gaz_audit,'textures':textures,'collisions':{'status':'DRAFT_SIMPLE_PROXIES','shapes':'part bounding boxes','count':len(collisions),'inertial_defined':False},'rig':{'armatures':[{'name':a.name,'bones':len(a.data.bones)} for a in armatures],'animations':[a.name for a in bpy.data.actions]},'exports':paths,'checks':{'source_loaded_in_blender':True,'unreal_import':'NOT_RUN','gazebo_import':'NOT_RUN','engine_scale_calibration':'NOT_RUN','physics_navigation_controls':'NOT_RUN','joint_axis_and_pivot_acceptance':'REVIEW_REQUIRED','normal_map_binding_in_engines':'NOT_RUN','non_manifold_visuals':'See per-part counts; open panels are not dynamic collision geometry'},'limitations':[]}
    if aid=='rover_1':metadata['limitations'].append('Tripo six-wheel candidate has the wrong wheel arrangement; native NASA Curiosity source is the delivered master. Source arm/mast pose is preserved; dynamic joint behavior remains unverified.')
    if aid=='scout_1':metadata['limitations'].append('Tripo produced 256 fragments. Blades were grouped geometrically into four rotor candidates and original UVs restored. Rotor/guard separation requires visual review before joint binding.')
    if aid=='science_station':metadata['limitations'].append('Four legs were generated; station is delivered in a fixed deployed pose. Folding limits are undefined.')
    if aid=='habitat':metadata['limitations'].append('NASA source part 1 is used; source part 2 is an optional reference. The airlock end door is separated for presentation. Interior, hinge operation and ingress collision remain unverified.')
    if aid=='sample_tube':metadata['limitations'].append('The printable NASA STL was split into a tube and a separate scenario cap at source z=4.05. The cut was closed; flight sealing, internal volume and sample containment are not modeled.')
    if aid=='sample_case':metadata['limitations'].append('CC0 industrial container is a scenario carrying/cache case. Sterility and sample containment are not physically modeled.')
    if aid.startswith('tool_'):metadata['limitations'].append('Tripo SCENARIO instrument appearance; not flight CAD, measured geometry, sensor optics or calibrated detection/illumination physics.')
    if spec_source=='nasa':metadata['limitations'].append('NASA source provides diffuse/AO art, not calibrated instrument optics or measured material channels.')
    (folder/'asset.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'master.blend'))
    views(objects,folder/'preview',('perspective','front','side','back'),640)
    if armatures:
        # Evaluate both animation clips after LOD reduction and capture deformation.
        arm=armatures[0];arm.data.pose_position='POSE'
        bpy.context.scene.frame_set(15)
        bpy.context.view_layer.update()
        views(objects,folder/'preview/animation',('perspective','back'),640)
        arm.data.pose_position='REST'
    print('PACKAGE_DONE',aid,lod0['triangles'],'triangles;',gaz_audit['triangles'],'Gazebo;',len(objects),'parts',flush=True)


if __name__=='__main__':
    ids=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(SPECS)
    for aid in ids:build(aid)
