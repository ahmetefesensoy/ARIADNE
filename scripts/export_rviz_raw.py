"""Encode exact accepted RViz source PNGs at their recorded arrival times."""
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();m=json.loads((a.folder/'manifest.json').read_text());frames=m['frames']
if not m['complete'] or m['failure']:raise SystemExit('Incomplete RViz capture')
lines=['ffconcat version 1.0']
for i,f in enumerate(frames):
 src=(a.folder/f['path']).resolve()
 if hashlib.sha256(src.read_bytes()).hexdigest()!=f['png_sha256']:raise SystemExit('Hash mismatch')
 lines.append("file '"+src.as_posix().replace("'","'\\''")+"'")
 if i+1<len(frames):lines.append('duration %.9f'%(frames[i+1]['elapsed_wall_s']-f['elapsed_wall_s']))
lst=a.folder/'raw.ffconcat';lst.write_text('\n'.join(lines)+'\n');a.output.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['ffmpeg','-v','error','-n','-safe','0','-f','concat','-i',str(lst),'-an','-fps_mode','vfr','-c:v','libx264','-threads','4','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(a.output)],check=True)
shutil.copy2(a.folder/'manifest.json',a.output.with_suffix('.source.json'))
