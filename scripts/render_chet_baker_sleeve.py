"""Original vector sleeve for the requested Chet Baker prop; no copied album art.

The name identifies the user's fictional personal-collection prop. This is not
an official album cover, a portrait, a recording licence or an endorsement.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, PathPatch, Rectangle
from matplotlib.path import Path as DrawPath
from matplotlib.font_manager import FontProperties

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/narrative/prologue_v1'
SERIF=FontProperties(fname='/mnt/c/Windows/Fonts/georgiab.ttf')
SANS=FontProperties(fname='/mnt/c/Windows/Fonts/segoeui.ttf')


def artwork(label=False):
    fig=plt.figure(figsize=(10,10),facecolor='#eee3ca')
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    ax.add_patch(Rectangle((.045,.045),.91,.91,fill=False,edgecolor='#203d3e',linewidth=1.4))
    if label:
        ax.add_patch(Circle((.5,.5),.47,color='#eee3ca'))
        ax.text(.5,.69,'CHET BAKER',ha='center',fontproperties=SERIF,fontsize=43,color='#193538')
        ax.text(.5,.3,'PERSONAL COLLECTION',ha='center',fontproperties=SANS,fontsize=20,color='#193538')
        ax.text(.5,.24,'JAZZ',ha='center',fontproperties=SANS,fontsize=20,color='#9b3d2c')
        ax.add_patch(Circle((.5,.5),.05,color='#111817'))
    else:
        ax.text(.085,.91,'PERSONAL COLLECTION   /   JAZZ',fontproperties=SANS,fontsize=16,color='#334b48')
        ax.text(.075,.74,'CHET',fontproperties=SERIF,fontsize=91,color='#193538')
        ax.text(.075,.59,'BAKER',fontproperties=SERIF,fontsize=91,color='#193538')
        ax.add_patch(Circle((.75,.31),.23,color='#245457'))
        # Original trumpet line work, not traced from a photograph or album.
        path=DrawPath([(.16,.29),(.2,.29),(.23,.43),(.34,.43),(.37,.29),(.67,.29),(.72,.32),(.82,.36)],
                      [DrawPath.MOVETO,DrawPath.LINETO,DrawPath.CURVE3,DrawPath.CURVE3,DrawPath.CURVE3,DrawPath.LINETO,DrawPath.LINETO,DrawPath.LINETO])
        ax.add_patch(PathPatch(path,fill=False,edgecolor='#c58a43',linewidth=13,capstyle='round'))
        ax.add_patch(Polygon([(.69,.28),(.86,.22),(.86,.41),(.69,.34)],closed=True,color='#d8a45b'))
        ax.add_patch(Polygon([(.85,.22),(.89,.21),(.89,.42),(.85,.41)],closed=True,color='#eee3ca'))
        for x in (.4,.46,.52):
            ax.add_patch(Rectangle((x,.285),.014,.15,color='#c58a43'))
            ax.add_patch(Rectangle((x-.014,.433),.043,.014,color='#193538'))
        ax.add_patch(Rectangle((.115,.292),.05,.018,color='#193538'))
        ax.text(.085,.13,'VARDİYA ARASI',fontproperties=SERIF,fontsize=24,color='#9b3d2c')
        ax.text(.085,.085,'ORIGINAL SLEEVE  /  MARS HABITAT COLLECTION',fontproperties=SANS,fontsize=10,color='#334b48')
    return fig


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    files=[]
    for base,is_label in [('chet_baker_sleeve',False),('chet_baker_label',True)]:
        fig=artwork(is_label)
        for ext in ('svg','png'):
            p=OUT/(base+'.'+ext)
            fig.savefig(p,dpi=140,facecolor=fig.get_facecolor())
            files.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        plt.close(fig)
    record={'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'SCENARIO',
            'method':'original code-native vector typography and trumpet drawing, no copied album art/portrait',
            'artist_name':'Chet Baker','official_album_cover':False,'recording_rights_granted':False,
            'font_files_not_redistributed':True,'generation_credits':0,'files':files}
    (OUT/'sleeve_provenance.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':main()
