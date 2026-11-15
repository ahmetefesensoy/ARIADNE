"""Export actual recorded frames, without titles, music, grading or cuts.

Keep the original game WAV separately: capture latency/duration is uncalibrated.
"""
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
from encode_unreal_shot import validate_manifest
p=argparse.ArgumentParser();p.add_argument('shot',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
folder=a.shot.resolve();m,frames=validate_manifest(folder);a.output.parent.mkdir(parents=True,exist_ok=True)
if a.output.exists():raise SystemExit('Preserving existing export')
lst=folder/'raw_export.ffconcat';lines=['ffconcat version 1.0']
for i,f in enumerate(frames):
 path=(folder/f['file']).as_posix().replace("'","'\\''");lines.append("file '"+path+"'")
 dt=frames[i+1]['captured_wall_s']-f['captured_wall_s'] if i+1<len(frames) else m['duration_wall_s']-f['captured_wall_s']
 lines.append('duration %.9f'%max(.001,dt))
lst.write_text('\n'.join(lines)+'\n')
subprocess.run(['ffmpeg','-v','error','-n','-safe','0','-f','concat','-i',str(lst),'-an','-fps_mode','vfr','-c:v','libx264','-threads','4','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output)],check=True)
audio=folder/'master.wav'
if audio.exists():shutil.copy2(audio,a.output.with_suffix('.game.wav'))
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(a.output)]))
r={'source_manifest':str(folder/'manifest.json'),'source_manifest_sha256':hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest(),'source_frames':len(frames),'recorded_at_utc':m['started_at_utc'],'export':'Uncut actual viewport frames. No added text/music/grade. Original game audio separate and not time-stretched. Existing game HUD is retained.','video_sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),'probe':probe}
a.output.with_suffix('.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'output':str(a.output),'frames':len(frames),'duration':probe['format']['duration']}))
