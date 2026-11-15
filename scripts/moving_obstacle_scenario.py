#!/usr/bin/env python3
"""Two SCENARIO kinematic crossing obstacles in Gazebo, sensed by live LiDAR.

Only Gazebo entity services are called. No maps, sensors, TF, rover velocity
or goals are published. Paths use simulation time and local DEM samples for
placement. These boxes are test fixtures, not Martian archive objects.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import signal
import subprocess
import time
import xml.etree.ElementTree as ET
import rclpy
from rosgraph_msgs.msg import Clock


def trajectory(physics_s, phase=0.):
    # A six-metre crossing, smooth reversals. Nominal max speed .25 m/s in
    # physics time; time acceleration changes wall rate, not scenario speed.
    return 3.0*math.sin(physics_s/12.0+phase)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terrain',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--duration',type=float,default=300)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not 10<=args.duration<=1800:parser.error('duration must be [10,1800] wall seconds')
    spec=importlib.util.spec_from_file_location('world',args.workspace/'src/redline_gazebo/scripts/prepare_world.py')
    world=importlib.util.module_from_spec(spec);spec.loader.exec_module(world)
    terrain=json.loads(args.terrain.read_text())
    for tile in terrain['meshes']:
        tile['collision_uri']=(args.terrain.parent/tile.get('collision_relative_path',tile['relative_path'])).resolve().as_uri()
    # Precompute support along the fixed path, not hidden planner input.
    fixtures=[]
    for name,cx,cy,phase in [('SCENARIO_moving_crossing_1',145.,-304.,0.),
                              ('SCENARIO_moving_crossing_2',155.,-314.,1.7)]:
        knots=[(-3.+i*.5,world.terrain_height(terrain,cx-3.+i*.5,cy)) for i in range(13)]
        fixtures.append({'name':name,'cx':cx,'cy':cy,'phase':phase,'terrain_samples':knots})
    rclpy.init();node=rclpy.create_node('moving_obstacle_scenario');clock=[None]
    sub=node.create_subscription(Clock,'/clock',lambda message:clock.__setitem__(0,message.clock.sec+message.clock.nanosec/1e9),2)
    stopped=[False]
    signal.signal(signal.SIGINT,lambda *_:stopped.__setitem__(0,True))
    record={'observed_at_utc':datetime.now(timezone.utc).isoformat(),'status':'SCENARIO',
        'scope':'two .25m/s bounded kinematic crossing boxes, Gazebo-only authority','fixtures':fixtures,
        'pose_updates_acknowledged':0,'failed_updates':0,'samples':[],'complete':False}
    def service(endpoint,kind,payload):
        return subprocess.run(['gz','service','-s','/world/bxw/'+endpoint,'--reqtype','gz.msgs.'+kind,
            '--reptype','gz.msgs.Boolean','--timeout','1500','--req',payload],capture_output=True,text=True,timeout=3)
    try:
        for fixture in fixtures:
            # Created once, then continuously moved by the scenario authority.
            ground=fixture['terrain_samples'][6][1]
            sdf=ET.Element('sdf',version='1.9');model=ET.SubElement(sdf,'model',name=fixture['name'])
            ET.SubElement(model,'static').text='true'
            ET.SubElement(model,'pose').text=f"{fixture['cx']} {fixture['cy']} {ground+1.5} 0 0 0"
            link=ET.SubElement(model,'link',name='fixture')
            for kind in ('visual','collision'):
                box=ET.SubElement(ET.SubElement(ET.SubElement(link,kind,name=kind),'geometry'),'box')
                ET.SubElement(box,'size').text='1.2 1.2 3.5'
            response=service('create','EntityFactory','sdf: '+json.dumps(ET.tostring(sdf,encoding='unicode')))
            if response.returncode or 'data: true' not in response.stdout:raise RuntimeError('Creation failed: '+fixture['name'])
        start=time.monotonic();last=-1.;base=None
        while not stopped[0] and time.monotonic()-start<args.duration:
            rclpy.spin_once(node,timeout_sec=.01)
            if clock[0] is None:continue
            if base is None:base=clock[0]
            elapsed=clock[0]-base
            if elapsed-last<.15:continue
            last=elapsed
            poses=[]
            for fixture in fixtures:
                offset=trajectory(elapsed,fixture['phase']);index=min(11,max(0,int((offset+3)/.5)))
                x0,z0=fixture['terrain_samples'][index];x1,z1=fixture['terrain_samples'][index+1]
                z=z0+(z1-z0)*(offset-x0)/(x1-x0)+1.5
                poses.append(f"pose: {{name: \"{fixture['name']}\" position: {{x: {fixture['cx']+offset} y: {fixture['cy']} z: {z}}} orientation: {{w: 1}}}}")
            response=service('set_pose_vector','Pose_V',' '.join(poses))
            if response.returncode==0 and 'data: true' in response.stdout:record['pose_updates_acknowledged']+=1
            else:record['failed_updates']+=1
            if len(record['samples'])<300:record['samples'].append({'wall_s':time.monotonic()-start,'physics_elapsed_s':elapsed,
                'x_m':[fixture['cx']+trajectory(elapsed,fixture['phase']) for fixture in fixtures]})
        record['complete']=True
    except Exception as error:record['error']=str(error)
    finally:
        args.out.write_text(json.dumps(record,indent=2)+'\n')
        node.destroy_node();rclpy.try_shutdown()
    return 0 if record['complete'] and record['failed_updates']==0 else 1


if __name__=='__main__':raise SystemExit(main())
