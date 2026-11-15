"""Neutral inspection renders; no mission scene or level content is authored."""
import math
import bpy
from mathutils import Vector


def bounds(objects):
    import numpy as np
    lows=[];highs=[]
    for o in objects:
        if not len(o.data.vertices):continue
        values=np.empty(len(o.data.vertices)*3,dtype=np.float64)
        o.data.vertices.foreach_get('co',values)
        points=values.reshape(-1,3)@np.array(o.matrix_world.to_3x3()).T+np.array(o.matrix_world.translation)
        lows.append(points.min(axis=0));highs.append(points.max(axis=0))
    if not lows:raise ValueError('No mesh vertices')
    return Vector(np.min(lows,axis=0)),Vector(np.max(highs,axis=0))


def views(objects, out, names=("perspective","front","side","back"), resolution=640):
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.samples=16
    scene.cycles.use_denoising=True
    scene.render.resolution_x=resolution
    scene.render.resolution_y=resolution
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=True
    scene.world=bpy.data.worlds.new("Inspection_world")
    scene.world.use_nodes=True
    scene.world.node_tree.nodes.get("Background").inputs[0].default_value=(0.25,0.25,0.25,1)
    scene.world.node_tree.nodes.get("Background").inputs[1].default_value=0.45
    low,high=bounds(objects)
    center=(low+high)*0.5
    span=max(high-low)
    camera=bpy.data.objects.new("CAM_Inspection",bpy.data.cameras.new("Inspection"))
    scene.collection.objects.link(camera)
    camera.data.type="ORTHO"
    camera.data.ortho_scale=span*1.45
    camera.data.clip_end=max(1000,span*100)
    camera.data.clip_start=max(0.0001,span*0.001)
    scene.camera=camera
    helpers=[camera]
    for name,offset,power in [("Key",(2,-3,4),850),("Fill",(-3,-1,2),550),("Rim",(0,4,3),1100)]:
        data=bpy.data.lights.new("Inspection_"+name,"AREA")
        data.energy=power*span*span
        data.shape="DISK"
        data.size=span*3
        light=bpy.data.objects.new("LGT_"+name,data)
        scene.collection.objects.link(light)
        light.location=center+Vector(offset)*span
        light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
        helpers.append(light)
    out.mkdir(parents=True,exist_ok=True)
    directions={"perspective":(3,-4,2.3),"front":(4,0,0.15),"side":(0,-4,0.15),"back":(-4,0,0.15),"top":(0,0,4)}
    for name in names:
        camera.location=center+Vector(directions[name])*span
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/(name+".png"))
        bpy.ops.render.render(write_still=True)
    for obj in helpers:
        bpy.data.objects.remove(obj,do_unlink=True)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    ROOT=Path(__file__).resolve().parents[1]
    args=sys.argv[sys.argv.index('--')+1:]
    for aid in args:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        folder=ROOT/"incoming"/aid
        bpy.ops.import_scene.gltf(filepath=str(folder/"source.glb"))
        meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
        views(meshes,folder/"preview/source",("perspective","front","side","back","top"),512)
