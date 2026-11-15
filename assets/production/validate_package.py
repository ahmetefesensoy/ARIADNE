"""Blender reload, FBX/OBJ round trips, pivots, rig and unit calibration evidence."""
from __future__ import annotations
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from build_package import export_fbx, write_obj, select
from preview import bounds, views


def main():
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'blender':bpy.app.version_string,'scope':'Blender file/geometry evidence only; no engine import or robot dynamics acceptance','assets':{},'calibration':{}}
    folder=ROOT/'calibration';folder.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,0.5));cube=bpy.context.object;cube.name='SM_Calibration_1m'
    export_fbx(folder/'calibration_1m.fbx',[cube])
    write_obj(folder/'calibration_1m.obj',[cube])
    arrows=[]
    for axis,vec,color in [('X',(1,0,0),(0.8,0.03,0.02,1)),('Y',(0,1,0),(0.03,0.65,0.05,1)),('Z',(0,0,1),(0.02,0.15,0.8,1))]:
        direction=Vector(vec)
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=0.025,depth=1,location=direction*0.5)
        stem=bpy.context.object;stem.name='SM_Axis_'+axis+'_stem';stem.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
        bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=0.08,depth=0.2,location=direction*1.1)
        head=bpy.context.object;head.name='SM_Axis_'+axis+'_head';head.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
        mat=bpy.data.materials.new('MAT_Axis_'+axis);mat.diffuse_color=color
        for part in (stem,head):part.data.materials.append(mat);arrows.append(part)
    export_fbx(folder/'axes.fbx',arrows);write_obj(folder/'axes.obj',arrows)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'calibration.blend'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(folder/'calibration_1m.fbx'))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    dim=bounds(objects)[1]-bounds(objects)[0]
    report['calibration']={'fbx_roundtrip_m':list(dim),'pass':max(abs(v-1) for v in dim)<1e-5,'expected_unreal_cm':[100,100,100],'unreal_measurement':'NOT_RUN','gazebo_measurement':'NOT_RUN'}
    for metadata in sorted((ROOT/'incoming').glob('*/asset.json')):
        aid=metadata.parent.name;folder=metadata.parent;data=json.loads(metadata.read_text())
        bpy.ops.wm.open_mainfile(filepath=str(folder/'master.blend'),load_ui=False,use_scripts=False)
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('SM_') or o.name.startswith('SK_')) and o.name.endswith('LOD0')]
        low,high=bounds(objects);expected=high-low
        result={'master_loaded':True,'mesh_count':len(objects),'triangles':sum(len(o.data.loop_triangles) if o.data.loop_triangles else sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects),'dimensions_m':list(expected),'source_metadata_dimensions_error_m':max(abs(a-b) for a,b in zip(expected,data['master']['dimensions_m'])),'nonfinite_vertices':0,'uv_missing_parts':[],'max_skin_influences':0,'rotation_checks':[]}
        for o in objects:
            if not o.data.uv_layers:result['uv_missing_parts'].append(o.name)
            coords=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',coords)
            result['nonfinite_vertices']+=int((~np.isfinite(coords)).sum())
            if any(m.type=='ARMATURE' for m in o.modifiers):
                result['max_skin_influences']=max(len([g for g in v.groups if g.weight>0]) for v in o.data.vertices)
            if any(w in o.name.lower() for w in ('wheel','rotor')):
                o.rotation_mode='XYZ'
                before=o.matrix_world.translation.copy();basis=o.rotation_euler.copy()
                point_before=o.matrix_world@o.data.vertices[0].co
                o.rotation_euler.rotate_axis('Y' if 'wheel' in o.name else 'Z',math.pi/2)
                bpy.context.view_layer.update()
                result['rotation_checks'].append({'part':o.name,'angle_deg':90,'pivot_drift_m':(o.matrix_world.translation-before).length,'vertex_displacement_m':(o.matrix_world@o.data.vertices[0].co-point_before).length,'finite':all(math.isfinite(v) for row in o.matrix_world for v in row)})
                o.rotation_euler=basis
        result['required_wheel_groups']=6 if aid=='rover_1' else 12 if aid=='pr_1' else None
        result['wheel_groups']=sum('wheel' in o.name.lower() for o in objects)
        result['rotor_groups']=sum('rotor' in o.name.lower() for o in objects)
        # The exact neutral assembled bounds must survive Blender's FBX importer.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(folder/'unreal'/f'{aid}_LOD0.fbx'))
        imported=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('UCX_')]
        actual=bounds(imported)[1]-bounds(imported)[0]
        result['fbx_reimport']={'mesh_count':len(imported),'dimensions_m':list(actual),'max_dimension_error_m':max(abs(a-b) for a,b in zip(expected,actual)),'armature_count':sum(o.type=='ARMATURE' for o in bpy.context.scene.objects),'animations':[a.name for a in bpy.data.actions]}
        bpy.ops.wm.read_factory_settings(use_empty=True)
        # The OBJ writer stores raw Blender +XYZ coordinates. Blender's import
        # basis is +Y forward/+Z up; use that to avoid rotating the stored mesh.
        bpy.ops.wm.obj_import(filepath=str(folder/'gazebo/assembly.obj'),forward_axis='Y',up_axis='Z')
        imported=[o for o in bpy.context.scene.objects if o.type=='MESH']
        actual=bounds(imported)[1]-bounds(imported)[0]
        result['obj_reimport']={'mesh_count':len(imported),'dimensions_m':list(actual),'max_dimension_error_m':max(abs(a-b) for a,b in zip(expected,actual))}
        result['pass']=bool(result['nonfinite_vertices']==0 and result['fbx_reimport']['max_dimension_error_m']<0.001 and result['obj_reimport']['max_dimension_error_m']<0.04 and (result['required_wheel_groups'] is None or result['wheel_groups']==result['required_wheel_groups']) and (aid!='scout_1' or result['rotor_groups']==4) and result['max_skin_influences']<=4)
        report['assets'][aid]=result
        print('VALIDATED',aid,result['pass'],'FBX delta',result['fbx_reimport']['max_dimension_error_m'],'OBJ delta',result['obj_reimport']['max_dimension_error_m'],flush=True)
    target=ROOT/'verification.json';target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('REPORT',target,flush=True)


if __name__=='__main__':main()
