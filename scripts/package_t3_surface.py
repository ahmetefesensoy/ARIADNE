#!/usr/bin/env python3
"""Add orbital UV imagery to immutable T3 terrain, preserving physics geometry."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def geometry_signature(path):
    """Compare ordered vertex positions and triangle vertex indices, ignoring UVs."""
    value=hashlib.sha256()
    with Path(path).open(encoding='ascii') as stream:
        for line in stream:
            fields=line.split()
            if not fields:continue
            if fields[0]=='v':value.update(('v '+' '.join(fields[1:4])+'\n').encode('ascii'))
            elif fields[0]=='f':value.update(('f '+' '.join(p.split('/')[0] for p in fields[1:])+'\n').encode('ascii'))
    return value.hexdigest()


def add_uv(source, destination, tile, bounds, material):
    left,bottom,right,top=bounds
    if not left<right or not bottom<top:raise ValueError('Invalid atlas bounds')
    count=0
    with Path(source).open(encoding='ascii') as src, Path(destination).open('x',encoding='ascii',newline='\n') as out:
        out.write(f'# DERIVED orbital imagery; unchanged T3 vertices/triangles\nmtllib {material}.mtl\nusemtl MAT_{material}\n')
        for line in src:
            fields=line.split()
            if not fields:continue
            if fields[0]=='v':
                count+=1
                x,y=map(float,fields[1:3]);x+=tile['pose_map_m'][0];y+=tile['pose_map_m'][1]
                u,v=(x-left)/(right-left),(y-bottom)/(top-bottom)
                if not -1e-7<=u<=1+1e-7 or not -1e-7<=v<=1+1e-7:raise ValueError('Mesh outside its imagery atlas')
                out.write(line)
                # Image rows run north->south; OBJ v runs bottom->top.
                out.write(f'vt {u:.12f} {v:.12f}\n')
            elif fields[0]=='f':
                vertices=[]
                for item in fields[1:]:
                    tokens=item.split('/');index=int(tokens[0]);normal=int(tokens[-1])
                    if not 1<=index<=count or not normal>0:raise ValueError('Invalid mesh face index')
                    vertices.append(f'{index}/{index}/{normal}')
                out.write('f '+' '.join(vertices)+'\n')
            else:out.write(line)
    if geometry_signature(source)!=geometry_signature(destination):raise ValueError('UV export changed physics geometry')
    return {'uvs':count,'uv_bounds':[0,0,1,1], 'geometry_sha256':geometry_signature(source)}


def package(terrain_path, imagery_path, output):
    terrain_path=Path(terrain_path).resolve();imagery_path=Path(imagery_path).resolve();output=Path(output).resolve()
    terrain=json.loads(terrain_path.read_text());imagery=json.loads(imagery_path.read_text())
    if output.exists():raise ValueError('Choose a new surface output directory; previous evidence is immutable')
    if imagery['origin']!=terrain['map_origin']:
        raise ValueError('Imagery and terrain must share the exact T1 ENU origin')
    output.mkdir(parents=True)
    shutil.copyfile(imagery_path,output/'imagery.json')
    for name in ('ops','context'):
        atlas=imagery['atlases'][name];source=imagery_path.parent/atlas['relative_path']
        if digest(source)!=atlas['sha256']:raise ValueError('Imagery atlas hash mismatch')
        shutil.copyfile(source,output/source.name)
        (output/f'terrain_{name}.mtl').write_text(
            f'newmtl MAT_terrain_{name}\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nd 1\nillum 1\nmap_Kd {source.name}\n',encoding='ascii')
    for tile in terrain['meshes']:
        original=terrain_path.parent/tile['relative_path']
        if digest(original)!=tile['sha256']:raise ValueError('Terrain source hash mismatch')
        collision=output/original.name;shutil.copyfile(original,collision)
        role='ops' if tile['id'].startswith('ops_') else 'context'
        visual=output/(original.stem+'_visual.obj')
        uv=add_uv(original,visual,tile,imagery['atlases'][role]['bounds_map_m'],f'terrain_{role}')
        tile.update(collision_relative_path=collision.name,visual_relative_path=visual.name,
                    visual_uri=visual.name,collision_uri=collision.name,
                    visual_sha256=digest(visual),collision_sha256=digest(collision),
                    visual_collision_identical=False,visual_collision_geometry_identical=True,**uv)
    for name in ('image','yaml'):
        source=terrain_path.parent/terrain['nav'][name];shutil.copyfile(source,output/source.name)
    uv_tests=[]
    for point in terrain['qa']['three_point_test']:
        x,y=point['map_x_m'],point['map_y_m']
        left,bottom,right,top=imagery['atlases']['ops']['bounds_map_m']
        u,v=(x-left)/(right-left),(y-bottom)/(top-bottom)
        error=max(abs((left+u*(right-left))-x),abs((bottom+v*(top-bottom))-y))
        uv_tests.append({'id':point['id'],'map_xy_m':[x,y],'uv':[u,v],
                         'inverse_error_m':error,'passed':error<=1e-7})
    if not all(p['passed'] for p in uv_tests):raise ValueError('UV coordinate roundtrip failed')
    terrain['qa']['uv_three_point_test']=uv_tests
    terrain['qa']['visual_collision_same_artifact']=False
    terrain['qa']['visual_collision_geometry_identical']=True
    terrain.update(surface_status='DERIVED',surface_algorithm='redline-orbital-surface-v1',
                   surface_created_at=datetime.now(timezone.utc).isoformat(),
                   terrain_source_manifest_sha256=digest(terrain_path),imagery_manifest_sha256=digest(imagery_path),
                   imagery_relative_path='imagery.json',
                   engine_contract={'master_frame':'map ENU; x east y north z up; metres',
                                    'ros_to_unreal_position_cm':['100*x','-100*y','100*z'],
                                    'gazebo_physics_authority':True,'unreal_import_verified':False},
                   limits=terrain.get('limits',[])+[
                       'Orbital appearance is not a measured material, traction or mineral layer.',
                       'DEM posting is not sub-metre terrain accuracy; no synthetic geometric detail added.',
                       'CRS/pixel/UV checks do not independently establish absolute feature alignment.'])
    terrain['artifacts']=[{'relative_path':p.name,'sha256':digest(p),'bytes':p.stat().st_size}
                          for p in sorted(output.iterdir()) if p.is_file()]
    (output/'manifest.json').write_text(json.dumps(terrain,indent=2)+'\n')
    print(json.dumps({'surface':str(output/'manifest.json'),'meshes':len(terrain['meshes']),
                      'triangles':terrain['budgets']['triangles'],'passed':True},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terrain',required=True,type=Path);parser.add_argument('--imagery',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    package(args.terrain,args.imagery,args.out)
