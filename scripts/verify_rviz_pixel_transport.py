"""Read-only exact PNG transport verification from real RViz, via rosbridge."""
import asyncio,base64,hashlib,json,argparse
from pathlib import Path
import websockets
async def run(args):
    frames={};statuses={};args.out.mkdir(parents=True,exist_ok=True)
    async with websockets.connect(args.url,max_size=2000000) as ws:
        for topic,typ in (('/redline/rviz/image/compressed','sensor_msgs/msg/CompressedImage'),('/redline/rviz/status','std_msgs/msg/String')):
            await ws.send(json.dumps({'op':'subscribe','topic':topic,'type':typ,'queue_length':1}))
        while True:
            e=json.loads(await asyncio.wait_for(ws.recv(),8));topic=e.get('topic');m=e.get('msg',{})
            if topic=='/redline/rviz/image/compressed':
                raw=base64.b64decode(m['data']);stamp=m['header']['stamp'];key=(stamp['sec'],stamp['nanosec']);frames[key]=raw
                if len(frames)>8:frames.pop(next(iter(frames)))
            elif topic=='/redline/rviz/status':
                s=json.loads(m['data']);key=(s['image_stamp_sec'],s['image_stamp_nanosec']);statuses[key]=s
                if len(statuses)>8:statuses.pop(next(iter(statuses)))
            else:continue
            s=statuses.get(key);raw=frames.get(key)
            if s and raw and s['capture_fresh']:
                actual=hashlib.sha256(raw).hexdigest();passed=actual==s['png_sha256'] and raw.startswith(b'\x89PNG\r\n\x1a\n')
                (args.out/'received-frame.png').write_bytes(raw)
                report={'passed':passed,'source':s['source'],'stream_id':s['stream_id'],'sequence':s['sequence'],
                    'source_png_sha256':s['png_sha256'],'received_png_sha256':actual,'width':s['width'],'height':s['height'],
                    'scope':'Exact lossless pixels from owned real RViz renderer through ROS and rosbridge; no redrawn map or user desktop'}
                (args.out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return 0 if passed else 1
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--out',required=True,type=Path);raise SystemExit(asyncio.run(run(p.parse_args())))
