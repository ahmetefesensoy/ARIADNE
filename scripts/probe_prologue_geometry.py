"""Read-only rays for generated visual facing, interior floors and clearances.

The optional airlock is inspected only after its derivative exists. Blender
coordinates are right handed; FBX import maps +Y to Unreal -Y. No asset is saved.
"""
import bpy
from mathutils import Vector
from pathlib import Path
import json,sys
root = Path(sys.argv[sys.argv.index('--')+1])
result = {}
for name in ('lounge','turntable','airlock','command','lab','corridor'):
    path = root/f'data/engines/prologue-tripo-v1/prologue_{name}/derived.blend'
    if not path.exists():
        if name in ('airlock','command','lab','corridor'):continue
        raise FileNotFoundError(path)
    bpy.ops.wm.open_mainfile(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.type=='MESH']
    if not meshes:raise RuntimeError('No render mesh for '+name)
    points = [o.matrix_world @ Vector(corner) for o in meshes for corner in o.bound_box]
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    height = 2.4 if name=='lounge' else .4 if name=='turntable' else (high.z+low.z)*.5
    origin = Vector((0,0,height))
    directions = {'+X':(1,0,0),'-X':(-1,0,0),'+Y':(0,1,0),'-Y':(0,-1,0),'floor':(0,0,-1),'top':(0,0,1)}
    probes = {}
    for key,direction in directions.items():
        nearest = None
        for mesh in meshes:
            inverse = mesh.matrix_world.inverted()
            local_origin = inverse @ origin
            local_direction = inverse.to_3x3() @ Vector(direction)
            found,point,normal,index = mesh.ray_cast(local_origin,local_direction.normalized(),distance=15)
            if not found:continue
            world_point = mesh.matrix_world @ point
            distance = (world_point-origin).length
            if nearest is None or distance<nearest[0]:nearest = (distance,world_point)
        probes[key] = {'hit':nearest is not None,'point':list(nearest[1]) if nearest else None,
                       'distance_m':nearest[0] if nearest else None}
    probes['bounds_m'] = {'low':list(low),'high':list(high)}
    probes['ray_origin_m'] = list(origin)
    probes['open_cardinal_axes'] = [key for key in ('+X','-X','+Y','-Y') if not probes[key]['hit']]
    probes['note'] = 'Read-only visual-mesh rays, not a physical pressure/collision validation; Blender +Y maps to UE -Y'
    result[name] = probes
for path in (root/'test-results/prologue-geometry-probes.json',root/'data/engines/prologue-tripo-v1/anchors.json'):
    path.write_text(json.dumps(result,indent=2))
