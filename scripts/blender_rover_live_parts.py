"""Split existing NASA-derived master into body and six local-pivot wheels.

No source edits, new art, remeshing or scale change. CLI fallback is used because
this environment exposes no Blender MCP connection. Output remains SCENARIO art.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector

repo = Path(sys.argv[sys.argv.index('--')+1]).resolve()
source = repo/'assets/incoming/rover_1'
out = repo/'data/engines/rover-live-parts-v1'
out.mkdir(parents=True, exist_ok=True)
asset = json.loads((source/'asset.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(source/'master.blend'))
parts = {part['name']: part for part in asset['parts']}
objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and obj.name in parts]
wheel_names = ['wheel_01_L','wheel_02_L','wheel_03_L','wheel_01_R','wheel_02_R','wheel_03_R']
by_source = {part['source_name']: part for part in asset['parts']}
wheel_objects = {name: next(obj for obj in objects if obj.name == by_source[name]['name']) for name in wheel_names}
report = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'SCENARIO',
          'source': str(source/'master.blend'), 'source_sha256': hashlib.sha256((source/'master.blend').read_bytes()).hexdigest(),
          'source_notice': 'NASA/JPL-Caltech original visual; see assets/incoming/rover_1/SOURCE.md',
          'source_modified': False, 'checks': [], 'exports': []}
original_triangles = sum(sum(max(0,len(poly.vertices)-2) for poly in obj.data.polygons) for obj in objects)
if len(objects) != 82 or original_triangles > 60000:
    raise RuntimeError(f'Unexpected delivered asset object/triangle count: {len(objects)}, {original_triangles}')
report['pre_export_audit'] = {'passed': True, 'objects': len(objects), 'triangles': original_triangles,
                             'scope': 'source-preserving runtime split, not retopology/material repair',
                             'unit_scale': 1,
                             'source_meshes_without_uv_preserved': [obj.name for obj in objects if not obj.data.uv_layers],
                             'open_visual_panels': 'Preserved; not collision geometry'}
collection = bpy.data.collections.new('DERIVED_RUNTIME_EXPORT')
bpy.context.scene.collection.children.link(collection)
for group, members, pivot in [('body', [obj for obj in objects if obj not in wheel_objects.values()], Vector((0,0,0)))] + [
        (name, [obj], Vector(by_source[name]['pivot_m'])) for name,obj in wheel_objects.items()]:
    copies = []
    for obj in members:
        mesh = obj.data.copy()
        transform = Matrix.Translation(-pivot) @ obj.matrix_world
        mesh.transform(transform)
        copy = bpy.data.objects.new('DERIVED_'+obj.name, mesh)
        collection.objects.link(copy)
        copies.append(copy)
    points = [vertex.co for obj in copies for vertex in obj.data.vertices]
    dimensions = [max(point[i] for point in points)-min(point[i] for point in points) for i in range(3)]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in copies:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    path = out/(group+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
        global_scale=1, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        axis_forward='-Y', axis_up='Z', use_mesh_modifiers=False, bake_anim=False,
        path_mode='RELATIVE', embed_textures=False)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    imported = [obj for obj in bpy.context.selected_objects if obj.type=='MESH']
    imported_points = [obj.matrix_world@vertex.co for obj in imported for vertex in obj.data.vertices]
    actual = [max(p[i] for p in imported_points)-min(p[i] for p in imported_points) for i in range(3)]
    error = max(abs(a-b) for a,b in zip(actual,dimensions))
    if error > 1e-5:
        raise RuntimeError('FBX unit/axis roundtrip failed: '+group)
    report['exports'].append({'part': group, 'file': path.name, 'dimensions_m': dimensions,
        'pivot_in_master_m': list(pivot), 'roundtrip_error_m': error,
        'triangles': sum(sum(max(0,len(p.vertices)-2) for p in obj.data.polygons) for obj in copies),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    for obj in imported+copies:
        bpy.data.objects.remove(obj, do_unlink=True)
report['passed'] = len(report['exports']) == 7
(out/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print('REDLINE_SPLIT '+json.dumps(report))
