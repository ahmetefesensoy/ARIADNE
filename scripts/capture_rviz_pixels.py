"""Record actual private-RViz ROS PNGs losslessly, without a desktop capture.

Read-only rosbridge subscriptions only. The receipt preserves wall arrival
times and original physics stamps; missing frames are gaps, not interpolated
data. No overlay, diagram, pose publisher, action or service command is used.
"""
from __future__ import annotations
import argparse
import asyncio
import base64
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import struct
import time
import websockets


async def record(args):
    args.out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();frames=[];pending={};statuses={};seen=set();stream_id=None;error=None;total=0;rejected=0
    manifest={'schema':'redline.rviz.pixel-capture.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'source':'Actual rviz2/private-xvfb PNG messages through ROS/rosbridge; no desktop or redrawn map',
        'url':args.url,'complete':False,'commands_sent':False,'requested_wall_s':args.seconds,'frames':frames}
    def save():
        manifest.update(saved_frames=len(frames),elapsed_wall_s=time.monotonic()-started,total_png_bytes=total,
                        rejected_frame_pairs=rejected,stream_id=stream_id,failure=error)
        (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    try:
        async with websockets.connect(args.url,max_size=2200000) as ws:
            for topic,typ in (('/redline/rviz/image/compressed','sensor_msgs/msg/CompressedImage'),('/redline/rviz/status','std_msgs/msg/String')):
                await ws.send(json.dumps({'op':'subscribe','topic':topic,'type':typ,'queue_length':2}))
            while time.monotonic()-started<args.seconds:
                remaining=args.seconds-(time.monotonic()-started)
                try:raw=await asyncio.wait_for(ws.recv(),min(3.,max(.01,remaining)))
                except TimeoutError:continue
                envelope=json.loads(raw);topic=envelope.get('topic');msg=envelope.get('msg',{})
                if topic=='/redline/rviz/image/compressed':
                    stamp=msg['header']['stamp'];key=(stamp['sec'],stamp['nanosec']);data=base64.b64decode(msg['data'],validate=True)
                    if len(data)>1024*1024:raise ValueError('source PNG exceeded1MiB stream contract')
                    pending[key]=(data,time.monotonic()-started)
                    if len(pending)>8:pending.pop(next(iter(pending)))
                elif topic=='/redline/rviz/status':
                    status=json.loads(msg['data']);key=(status['image_stamp_sec'],status['image_stamp_nanosec']);statuses[key]=status
                    if len(statuses)>8:statuses.pop(next(iter(statuses)))
                else:continue
                if key not in pending or key not in statuses:continue
                data,received=pending[key];status=statuses[key];identity=(status['stream_id'],status['sequence'])
                if identity in seen:continue
                seen.add(identity)
                if not (status.get('capture_fresh') and status.get('physics_fresh') and status.get('source')=='rviz2/private-xvfb'):
                    rejected+=1;continue
                digest=hashlib.sha256(data).hexdigest()
                if data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid PNG payload')
                if digest!=status.get('png_sha256'):
                    # Two render frames can share a paused physics stamp.
                    # Arrival order is not frame identity. Reject this pairing
                    # and wait for an exact matching source hash.
                    rejected+=1;continue
                width,height=struct.unpack('>II',data[16:24])
                if (width,height)!=(status.get('width'),status.get('height')) or not(1<=width<=1280 and 1<=height<=800):
                    raise ValueError('PNG dimensions disagree with source status')
                if stream_id is not None and stream_id!=status['stream_id']:raise ValueError('source stream/physics clock restarted during capture')
                stream_id=status['stream_id']
                if len(frames)>=600 or total+len(data)>256*1024*1024:raise ValueError('bounded capture limit reached')
                name=f'frame_{len(frames):06}.png';(args.out/name).write_bytes(data);total+=len(data)
                frames.append({'path':name,'elapsed_wall_s':received,'physics_stamp':{'sec':key[0],'nanosec':key[1]},
                    'source_sequence':status['sequence'],'png_sha256':digest,'width':width,'height':height})
                if len(frames)%20==0:save()
        manifest['complete']=len(frames)>=2
    except BaseException as exc:error=type(exc).__name__+': '+str(exc)
    finally:
        manifest['ended_at_utc']=datetime.now(timezone.utc).isoformat();save()
    print(json.dumps({k:v for k,v in manifest.items() if k!='frames'}))
    return 0 if manifest['complete'] and not error else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds',type=float,default=90)
    args=p.parse_args()
    if not 1<=args.seconds<=120:p.error('--seconds must be1..120 wall seconds')
    raise SystemExit(asyncio.run(record(args)))
