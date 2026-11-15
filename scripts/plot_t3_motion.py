#!/usr/bin/env python3
"""Plot observed physical trajectories, including failed attempts, without smoothing."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terrain',type=Path,required=True)
    parser.add_argument('--run',type=Path,action='append',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();terrain=json.loads(args.terrain.read_text());spawn=terrain['spawn'];goal=terrain['goal']
    origin=np.array([spawn['map_x_m'],spawn['map_y_m']]);sources=[]
    fig,ax=plt.subplots(figsize=(8,7),layout='constrained');colours=['#0072B2','#D55E00','#009E73']
    fig.get_layout_engine().set(rect=(0,.04,1,.96))
    for i,run in enumerate(args.run):
        source=run/'physical-motion.json';motion=json.loads(source.read_text())
        result=json.loads((run/'navigation_result.json').read_text())
        runtime_result=json.loads((run/'result.json').read_text())
        samples=motion['samples'];xy=np.array([s['xyz_m'][:2] for s in samples])-origin
        times=np.array([s['elapsed_wall_s'] for s in samples]);shown=xy.copy()
        if len(times)>1:shown[np.r_[False,np.diff(times)>.5]]=np.nan
        status='başarılı' if result['passed'] else 'başarısız'
        colour=colours[i%len(colours)]
        ax.plot(shown[:,0],shown[:,1],color=colour,lw=1.5,ls='-' if i%2 else '--',
                marker='.',ms=2,label=f"{run.name}: {status}\n{runtime_result['started_at_utc'][:19].replace('T',' ')} UTC")
        if len(samples):
            geometry=json.loads((run/'rover-geometry.json').read_text())
            for index in sorted({0,len(samples)//2,len(samples)-1}):
                sample=samples[index];x,y,z,w=sample['quaternion_xyzw']
                yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));c,s=math.cos(yaw),math.sin(yaw)
                body=np.array([[c*a-s*b,s*a+c*b] for a,b in geometry['footprint_m']])+xy[index]
                ax.add_patch(Polygon(body,closed=True,fill=False,edgecolor=colour,lw=.7,alpha=.6))
        sources.append({'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                        'run_passed':result['passed'],'samples':len(samples)})
    obstacle=5*np.array([math.cos(spawn['yaw_rad']),math.sin(spawn['yaw_rad'])])
    c,s=math.cos(spawn['yaw_rad']),math.sin(spawn['yaw_rad'])
    box=np.array([[c*a-s*b,s*a+c*b] for a,b in ((-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5))])+obstacle
    ax.add_patch(Polygon(box,closed=True,facecolor='#BBBBBB',edgecolor='black',hatch='///',label='SCENARIO test engeli'))
    ax.scatter([0],[0],marker='o',color='black',s=40,zorder=5,label='Başlangıç')
    target=np.array([goal['map_x_m'],goal['map_y_m']])-origin
    ax.scatter([target[0]],[target[1]],marker='*',color='black',s=100,zorder=5,label='Hedef')
    ax.set(xlabel='Başlangıca göre doğu (m)',ylabel='Başlangıca göre kuzey (m)',
           title='T3 — Gazebo’da ölçülen hareket (simülasyon)')
    ax.set_aspect('equal',adjustable='datalim');ax.margins(.2);ax.grid(alpha=.2)
    ax.legend(loc='upper left',fontsize=8)
    fig.text(.5,.015,'10 Hz duvar zamanı örnekleri; >0,5 s boşluklar kesilir. Kutular düzlemsel rover zarfıdır.',
             ha='center',fontsize=8)
    args.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(args.out,dpi=180);plt.close(fig)
    report={'created_at_utc':datetime.now(timezone.utc).isoformat(),'matplotlib':matplotlib.__version__,
        'sources':sources,'terrain_sha256':hashlib.sha256(args.terrain.read_bytes()).hexdigest(),
        'transform':'map ENU minus manifest spawn ENU; no rescaling or smoothing',
        'limits':['Single simulated route; not continuous collision proof, calibrated rover dynamics, or low-rock detection.',
                  'Footprint drawings use planar yaw; roll/pitch and height are not represented.'],
        'alt_text':'Başarısız ve güncel rover koşularının ölçülen yolları, başlangıç, hedef ve senaryo engeline göre karşılaştırılır.'}
    args.out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
