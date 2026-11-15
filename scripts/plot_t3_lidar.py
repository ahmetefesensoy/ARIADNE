#!/usr/bin/env python3
"""Measured XYZ snapshot: classified returns, no invented terrain surface."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();source=args.runtime/'perception-result.npz'
    data=np.load(source);report=json.loads((args.runtime/'perception-result.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    fig.get_layout_engine().set(rect=(0,.08,1,.9))
    fig.suptitle('T3 — Ölçülen 3D LiDAR dönüşleri (simülasyon)')
    for key,colour,marker,label in (('ground','#777777','.','Zemin desteği'),
                                    ('obstacles','#D55E00','x','Engel adayı')):
        points=data[key]
        if not len(points):continue
        local=points[np.hypot(points[:,0],points[:,1])<=8]
        axes[0].scatter(local[:,0],local[:,1],s=3 if key=='ground' else 15,c=colour,marker=marker,label=label)
        band=local[np.abs(local[:,1])<=.8]
        axes[1].scatter(band[:,0],band[:,2],s=5 if key=='ground' else 18,c=colour,marker=marker,label=label)
    axes[0].set(xlabel='Sensör +X (m)',ylabel='Sensör +Y (m)',title='Üstten görünüm: gözlenen noktalar')
    axes[1].set(xlabel='Sensör +X (m)',ylabel='Sensör +Z (m)',title='Merkez şerit: |Y| ≤ 0,8 m')
    for ax in axes:
        ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best')
    fig.text(.5,.04,f"{report['created_at_utc'][:19].replace('T',' ')} UTC • 360 × 32 ışın • sınıflar ROS filtresinin çıktısıdır",ha='center',fontsize=9)
    fig.text(.5,.012,'Tek sabit SCENARIO nesnesi; noktalar yüzey veya sürekli çarpışmasızlık kanıtı değildir.',ha='center',fontsize=8)
    args.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(args.out,dpi=160);plt.close(fig)
    metadata={'created_at_utc':datetime.now(timezone.utc).isoformat(),'source':str(source),
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'processing':'Only finite classified returns; radius<=8 m; side panel |Y|<=0.8 m. No smoothing, interpolation or rescaling.',
        'matplotlib':matplotlib.__version__,'alt_text':'Üstten ve yandan 3D LiDAR noktaları; gri zemin, turuncu çarpı engel adayı.',
        'limits':['One stationary simulated point cloud; uncertain terrain classes are not verified ground truth.']}
    args.out.with_suffix('.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
