"""Independently compose captured ROS TF/odometry and compare actual UE actor CSV."""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path


def multiply(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return [w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z]


def rotate(q,v):
    return multiply(multiply(q,[*v,0]),[-q[0],-q[1],-q[2],q[3]])[:3]


def xyz(value):return [float(value.get(k,0)) for k in ('x','y','z')]
def quat(value):return [float(value.get(k,0)) for k in ('x','y','z','w')]
def stamp(header):return int(header['stamp']['sec'])*1_000_000_000+int(header['stamp']['nanosec'])


def verify(feed,poses,physical_presentation=False):
    envelopes=[json.loads(line) for line in feed.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    transforms={};odometry={}
    for packet in envelopes:
        topic=packet['topic'];message=packet['msg']
        if topic in ('/tf_static','/redline/bridge/tf_static_snapshot'):
            for transform in message['transforms']:
                if transform['header']['frame_id']=='map' and transform['child_frame_id']=='rover_1/odom':transforms['map_odom']=transform['transform']
        elif topic==('/redline/presentation/rover_1/odom' if physical_presentation else '/rover_1/odom'):odometry[stamp(message['header'])]=message
    if not physical_presentation and 'map_odom' not in transforms:raise ValueError('Captured map->odom transform missing')
    transform=transforms.get('map_odom')
    if not physical_presentation:q0=quat(transform['rotation']);p0=xyz(transform['translation'])
    errors=[];rotation_errors=[];map_errors=[];matched=[]
    with poses.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            source=odometry.get(round(float(row['physics_stamp_sec'])*1_000_000_000))
            if source is None:continue
            if source['header']['frame_id']!=('map' if physical_presentation else 'rover_1/odom') or source['child_frame_id']!='rover_1/base_link':raise ValueError('Unexpected ROS frame')
            pose=source['pose']['pose']
            if physical_presentation:
                map_position=xyz(pose['position']);map_rotation=quat(pose['orientation'])
            else:
                rotated=rotate(q0,xyz(pose['position']))
                map_position=[a+b for a,b in zip(p0,rotated)];map_rotation=multiply(q0,quat(pose['orientation']))
            expected_position=[map_position[0]*100,-map_position[1]*100,map_position[2]*100]
            expected_rotation=[-map_rotation[0],map_rotation[1],-map_rotation[2],map_rotation[3]]
            actual_position=[float(row['ue_'+k+'_cm']) for k in ('x','y','z')]
            actual_rotation=[float(row['ue_q'+k]) for k in ('x','y','z','w')]
            norm=math.sqrt(sum(x*x for x in actual_rotation)*sum(x*x for x in expected_rotation))
            cosine=min(1,abs(sum(a*b for a,b in zip(actual_rotation,expected_rotation)))/norm)
            errors.append(math.dist(expected_position,actual_position)/100)
            map_errors.append(math.dist(map_position,[float(row['map_'+k+'_m']) for k in ('x','y','z')]))
            rotation_errors.append(2*math.acos(cosine));matched.append(float(row['physics_stamp_sec']))
    if len(errors)<10:raise ValueError(f'Only {len(errors)} exactly matched ROS physics stamps')
    return {'created_at_utc':datetime.now(timezone.utc).isoformat(),'passed':max(errors)<1e-4 and max(rotation_errors)<1e-4,
        'scope':('actual UE actor location/quaternion vs Gazebo physical map pose through display-only ROS adapter, exact source stamps' if physical_presentation else 'actual UE actor location/quaternion vs independently composed ROS TF and odometry, exact source stamps'),
        'matched_samples':len(errors),'physics_stamp_range_s':[min(matched),max(matched)],
        'max_position_error_m':max(errors),'max_rotation_error_rad':max(rotation_errors),'max_logged_map_error_m':max(map_errors),
        'map_from_odom':transform,'feed_sha256':hashlib.sha256(feed.read_bytes()).hexdigest(),
        'poses_sha256':hashlib.sha256(poses.read_bytes()).hexdigest(),
        'limits':[('Physical display routing only; not localization/nav truth or continuous wheel-contact proof.' if physical_presentation else 'Estimated ROS pose is compared; not independent rover localization truth or photorealistic scene acceptance.'),
                  'Technical UE presentation actor has physics/collision disabled.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--feed',type=Path,required=True)
    parser.add_argument('--poses',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--physical-presentation',action='store_true')
    args=parser.parse_args();report=verify(args.feed,args.poses,args.physical_presentation)
    args.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['passed'] else 1)
