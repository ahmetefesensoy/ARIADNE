#!/usr/bin/env python3
"""Assemble an offline Mars SDF from exact terrain meshes and scenario rover."""
import argparse
import copy
import hashlib
import json
import math
from urllib.parse import urlparse,unquote
from pathlib import Path
import xml.etree.ElementTree as ET
ET.register_namespace('gz','https://gazebosim.org/schemas')


def tag(parent,element,text=None,**attrs):
    node=ET.SubElement(parent,element,attrs)
    if text is not None:node.text=str(text)
    return node


def geometry_signature(path):
    result=hashlib.sha256()
    with Path(path).open(encoding='ascii') as stream:
        for line in stream:
            fields=line.split()
            if not fields:continue
            if fields[0]=='v':result.update(('v '+' '.join(fields[1:4])+'\n').encode('ascii'))
            elif fields[0]=='f':result.update(('f '+' '.join(p.split('/')[0] for p in fields[1:])+'\n').encode('ascii'))
    return result.hexdigest()


def terrain_height(manifest,x,y):
    """World construction only: sample the same verified collision triangles.

    This does not feed ground truth into sensor processing or navigation.
    """
    candidates=[tile for tile in manifest['meshes'] if tile.get('role')=='ops_1m' and
                tile['bounds_map_m'][0]<=x<=tile['bounds_map_m'][2] and
                tile['bounds_map_m'][1]<=y<=tile['bounds_map_m'][3]]
    for tile in candidates:
        pose=tile['pose_map_m']
        if any(abs(a)>1e-12 for a in pose[3:]):raise ValueError('Rotated terrain tile unsupported')
        uri=urlparse(tile['collision_uri'])
        path=Path(unquote(uri.path)) if uri.scheme=='file' else Path(tile['collision_uri'])
        vertices=[];px=x-pose[0];py=y-pose[1]
        with path.open() as stream:
            for line in stream:
                fields=line.split()
                if not fields:continue
                if fields[0]=='v':vertices.append(tuple(map(float,fields[1:4])))
                elif fields[0]=='f':
                    a,b,c=(vertices[int(part.split('/')[0])-1] for part in fields[1:4])
                    if not min(a[0],b[0],c[0])-1e-8<=px<=max(a[0],b[0],c[0])+1e-8:continue
                    if not min(a[1],b[1],c[1])-1e-8<=py<=max(a[1],b[1],c[1])+1e-8:continue
                    denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
                    if abs(denominator)<1e-12:continue
                    u=((b[1]-c[1])*(px-c[0])+(c[0]-b[0])*(py-c[1]))/denominator
                    v=((c[1]-a[1])*(px-c[0])+(a[0]-c[0])*(py-c[1]))/denominator
                    if min(u,v,1-u-v)>=-1e-8:return pose[2]+u*a[2]+v*b[2]+(1-u-v)*c[2]
    raise ValueError('Fixture position lacks verified fine collision support')


def assemble(rover_sdf, manifest=None, *, smoke=False, root_clearance=.5, obstacle_fixture=False, obstacle_height=3.5):
    sdf=ET.Element('sdf',version='1.9');world=tag(sdf,'world',name='bxw')
    tag(world,'gravity','0 0 -3.721')
    physics=tag(world,'physics',name='mars_1ms',type='ignored')
    tag(physics,'max_step_size',.001);tag(physics,'real_time_factor',1.0)
    for short,cls in [('physics','Physics'),('user-commands','UserCommands'),('scene-broadcaster','SceneBroadcaster'),('imu','Imu')]:
        tag(world,'plugin',filename=f'gz-sim-{short}-system',name=f'gz::sim::systems::{cls}')
    sensors=tag(world,'plugin',filename='gz-sim-sensors-system',name='gz::sim::systems::Sensors')
    tag(sensors,'render_engine','ogre2')
    scene=tag(world,'scene');tag(scene,'ambient','.5 .5 .5 1');tag(scene,'background','.3 .3 .3 1');tag(scene,'shadows','false')
    light=tag(world,'light',name='sun',type='directional')
    tag(light,'pose','0 0 100 0 0 0');tag(light,'diffuse','.8 .8 .8 1');tag(light,'direction','-.3 -.2 -1')
    if smoke:
        model=tag(world,'model',name='smoke_ground');tag(model,'static','true');link=tag(model,'link',name='ground')
        for kind in ('collision','visual'):
            node=tag(link,kind,name=kind);plane=tag(tag(node,'geometry'),'plane');tag(plane,'normal','0 0 1');tag(plane,'size','100 100')
        spawn={'map_x_m':0,'map_y_m':0,'ground_z_m':0,'yaw_rad':0}
    else:
        if not manifest or not manifest.get('meshes'):raise ValueError('Verified terrain mesh manifest required')
        for tile in manifest['meshes']:
            model=tag(world,'model',name=tile['id']);tag(model,'static','true')
            tag(model,'pose',' '.join(str(v) for v in tile['pose_map_m']))
            link=tag(model,'link',name='terrain')
            if tile['visual_uri']!=tile['collision_uri'] and not tile.get('visual_collision_geometry_identical'):
                raise ValueError('Terrain visual/collision must use the same geometry')
            for kind in ('visual','collision'):
                node=tag(link,kind,name=kind);tag(tag(tag(node,'geometry'),'mesh'),'uri',tile[f'{kind}_uri'])
        spawn=manifest['spawn']
    if obstacle_fixture:
        # Bounded commissioning target, deliberately tall enough for the current
        # high 2D scan. It is SCENARIO, not an observed Martian rock or level art.
        x=spawn['map_x_m']+5*math.cos(spawn['yaw_rad'])
        y=spawn['map_y_m']+5*math.sin(spawn['yaw_rad'])
        obstacle=tag(world,'model',name='SCENARIO_lidar_acceptance_obstacle')
        ground=0. if smoke else terrain_height(manifest,x,y)
        center_z=1.5 if obstacle_height==3.5 else obstacle_height/2-.05
        tag(obstacle,'static','true');tag(obstacle,'pose',f"{x} {y} {ground+center_z} 0 0 {spawn['yaw_rad']}")
        link=tag(obstacle,'link',name='fixture')
        for kind in ('visual','collision'):
            node=tag(link,kind,name=kind);tag(tag(tag(node,'geometry'),'box'),'size',f'1 1 {obstacle_height}')
    # Technical camera near the actual negative-elevation terrain. The default
    # world-origin camera would be thousands of metres above this Mars datum.
    gui=tag(world,'gui',fullscreen='false')
    view=tag(gui,'plugin',filename='MinimalScene',name='3D View')
    properties=tag(view,'gz-gui');tag(properties,'title','3D View')
    tag(properties,'property','false',type='bool',key='showTitleBar')
    tag(properties,'property','docked',type='string',key='state')
    tag(view,'engine','ogre2');tag(view,'scene','scene')
    tag(view,'camera_pose',f"{spawn['map_x_m']-65} {spawn['map_y_m']-65} {spawn['ground_z_m']+80} 0 0.715 0.785398")
    clip=tag(view,'camera_clip');tag(clip,'near',.1);tag(clip,'far',10000)
    for filename,name in [('GzSceneManager','Scene Manager'),('InteractiveViewControl','Interactive view control'),('CameraTracking','Camera Tracking')]:
        plugin=tag(gui,'plugin',filename=filename,name=name);properties=tag(plugin,'gz-gui')
        for key,value,kind in [('state','floating','string'),('width','5','double'),('height','5','double'),('showTitleBar','false','bool')]:
            tag(properties,'property',value,type=kind,key=key)
    rover=copy.deepcopy(ET.parse(rover_sdf).getroot().find('model'))
    if rover is None:raise ValueError('Missing rover SDF model')
    old=rover.find('pose')
    if old is not None:rover.remove(old)
    # Base centre .5m above wheel contact; .10m drop lets physics establish contact.
    tag(rover,'pose',f"{spawn['map_x_m']} {spawn['map_y_m']} {spawn['ground_z_m']+root_clearance+.10} 0 0 {spawn['yaw_rad']}")
    world.append(rover)
    return sdf


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rover',required=True,type=Path);p.add_argument('--terrain',type=Path)
    p.add_argument('--root-clearance',type=float,default=.5)
    p.add_argument('--obstacle-fixture',action='store_true')
    p.add_argument('--obstacle-height',type=float,default=3.5)
    p.add_argument('--smoke',action='store_true');p.add_argument('--out',required=True,type=Path)
    args=p.parse_args();manifest=json.loads(args.terrain.read_text()) if args.terrain else None
    if manifest:
        for tile in manifest['meshes']:
            signatures=[]
            for kind in ('visual','collision'):
                path=(args.terrain.parent/tile.get(kind+'_relative_path',tile['relative_path'])).resolve()
                with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
                if digest!=tile.get(kind+'_sha256',tile['sha256']):raise ValueError('Terrain mesh hash mismatch')
                tile[kind+'_uri']=path.as_uri()
                if tile.get('visual_collision_geometry_identical'):signatures.append(geometry_signature(path))
            if signatures and (len(set(signatures))!=1 or signatures[0]!=tile['geometry_sha256']):
                raise ValueError('Visual/collision geometry differs')
        if manifest.get('surface_algorithm'):
            for item in manifest['artifacts']:
                path=args.terrain.parent/item['relative_path']
                with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
                if digest!=item['sha256']:raise ValueError('Surface artifact hash mismatch')
    if not 0<args.root_clearance<3:raise ValueError('Invalid robot root clearance')
    if not .2<=args.obstacle_height<=4:raise ValueError('Invalid commissioning obstacle height')
    world=assemble(args.rover,manifest,smoke=args.smoke,root_clearance=args.root_clearance,
                   obstacle_fixture=args.obstacle_fixture,obstacle_height=args.obstacle_height);ET.indent(world)
    payload=ET.tostring(world,encoding='utf-8',xml_declaration=True)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    if args.out.exists():
        if args.out.read_bytes()!=payload:raise ValueError('World output differs; choose a new output path')
    else:
        with args.out.open('xb') as stream:stream.write(payload)
    print(args.out.resolve())

if __name__=='__main__':main()
