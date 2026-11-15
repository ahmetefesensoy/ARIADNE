#!/usr/bin/env python3
"""Read-only Gazebo ground truth for evaluation; never feeds localization/Nav2."""
import argparse
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import queue
import os
import signal
import subprocess
import threading
import time


def stream_poses(stream, pending):
    decoder=json.JSONDecoder();buffer=''
    try:
        for line in stream:
            buffer+=line
            if len(buffer)>2_000_000:raise ValueError('Invalid/oversized Gazebo JSON message')
            try:value,end=decoder.raw_decode(buffer.lstrip())
            except json.JSONDecodeError:continue
            buffer=buffer.lstrip()[end:].lstrip()
            for pose in value.get('pose',[]):
                if pose.get('name')=='rover_1':pending.put(pose)
    finally:pending.put(None)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--terrain',type=Path,required=True)
    args=parser.parse_args();spawn=json.loads(args.terrain.read_text())['spawn']
    pending=queue.Queue();samples=[];count=0;last_record=0;started=time.monotonic()
    process=subprocess.Popen(['gz','topic','-e','-t','/world/bxw/dynamic_pose/info','-d','280','--json-output'],
                             stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,start_new_session=True)
    thread=threading.Thread(target=stream_poses,args=(process.stdout,pending),daemon=True);thread.start()
    try:
        while time.monotonic()-started<285:
            if (args.runtime/'result.json').exists():break
            try:pose=pending.get(timeout=.2)
            except queue.Empty:continue
            if pose is None:break
            count+=1;now=time.monotonic()
            if now-last_record<.1:continue
            last_record=now;p=pose['position'];q=pose.get('orientation',{})
            xyz=[float(p.get(k,0)) for k in ('x','y','z')]
            quat=[float(q.get(k,1 if k=='w' else 0)) for k in ('x','y','z','w')]
            if not all(math.isfinite(v) for v in xyz+quat):raise ValueError('Non-finite ground truth')
            samples.append({'elapsed_wall_s':now-started,'xyz_m':xyz,'quaternion_xyzw':quat})
    except KeyboardInterrupt:pass
    finally:
        if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        along=[];cross=[];c=math.cos(spawn['yaw_rad']);s=math.sin(spawn['yaw_rad'])
        for sample in samples:
            x,y=sample['xyz_m'][:2];dx=x-spawn['map_x_m'];dy=y-spawn['map_y_m']
            along.append(c*dx+s*dy);cross.append(-s*dx+c*dy)
        report={'created_at_utc':datetime.now(timezone.utc).isoformat(),
            'evaluation_only':True,'input':'Gazebo /world/bxw/dynamic_pose/info, no ROS publisher',
            'received_model_poses':count,'samples':samples,'maximum_lateral_displacement_m':max(map(abs,cross),default=None),
            'maximum_forward_displacement_m':max(along,default=None),
            'limits':['Sampling is wall-time throttled at 10 Hz; not continuous collision proof.']}
        (args.runtime/'physical-motion.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
