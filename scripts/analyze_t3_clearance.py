#!/usr/bin/env python3
"""Independent sampled planar envelope check, never a navigation input."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path


def polygon_distance(a,b):
    separated=False
    for polygon in (a,b):
        for p,q in zip(polygon,polygon[1:]+polygon[:1]):
            nx,ny=p[1]-q[1],q[0]-p[0]
            pa=[x*nx+y*ny for x,y in a];pb=[x*nx+y*ny for x,y in b]
            if max(pa)<min(pb) or max(pb)<min(pa):separated=True
    if not separated:return 0.0
    distances=[]
    for points,edges in ((a,b),(b,a)):
        for p in points:
            for u,v in zip(edges,edges[1:]+edges[:1]):
                dx,dy=v[0]-u[0],v[1]-u[1];denom=dx*dx+dy*dy
                t=max(0,min(1,((p[0]-u[0])*dx+(p[1]-u[1])*dy)/denom)) if denom else 0
                distances.append(math.hypot(p[0]-u[0]-t*dx,p[1]-u[1]-t*dy))
    return min(distances)


def transform(polygon,x,y,yaw):
    c,s=math.cos(yaw),math.sin(yaw)
    return [(x+c*a-s*b,y+s*a+c*b) for a,b in polygon]


def analyze(runtime,terrain_path):
    result=json.loads((runtime/'result.json').read_text())
    if not result.get('obstacle_fixture'):raise ValueError('This run has no declared obstacle fixture')
    if result['terrain_sha256']!=hashlib.sha256(terrain_path.read_bytes()).hexdigest():raise ValueError('Terrain manifest mismatch')
    terrain=json.loads(terrain_path.read_text());spawn=terrain['spawn']
    motion_path=runtime/'physical-motion.json';motion=json.loads(motion_path.read_text())
    geometry=json.loads((runtime/'rover-geometry.json').read_text())
    yaw=spawn['yaw_rad'];x=spawn['map_x_m']+5*math.cos(yaw);y=spawn['map_y_m']+5*math.sin(yaw)
    box=transform([(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)],x,y,yaw)
    distances=[]
    for sample in motion['samples']:
        qx,qy,qz,qw=sample['quaternion_xyzw']
        heading=math.atan2(2*(qw*qz+qx*qy),1-2*(qy*qy+qz*qz))
        body=transform([tuple(p) for p in geometry['footprint_m']],*sample['xyz_m'][:2],heading)
        distances.append(polygon_distance(body,box))
    if not distances:raise ValueError('No physical pose observations')
    gaps=[b['elapsed_wall_s']-a['elapsed_wall_s'] for a,b in zip(motion['samples'],motion['samples'][1:])]
    return {'created_at_utc':datetime.now(timezone.utc).isoformat(),'evaluation_only':True,
        'physical_motion_sha256':hashlib.sha256(motion_path.read_bytes()).hexdigest(),
        'minimum_sampled_planar_clearance_m':min(distances),'sample_count':len(distances),
        'maximum_sample_gap_wall_s':max(gaps,default=0),'envelope_overlap_samples':sum(d==0 for d in distances),
        'navigation_passed':result['passed'],
        'limits':['Yaw-only delivered envelope vs SCENARIO fixture; roll/pitch and height are not represented.',
                  'Samples are not a continuous collision-free or hardware-safety proof.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--terrain',type=Path,required=True)
    args=parser.parse_args();report=analyze(args.runtime,args.terrain)
    (args.runtime/'clearance-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
