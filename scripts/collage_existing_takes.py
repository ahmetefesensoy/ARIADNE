"""Place existing takes side by side, preserving source files and playback speed."""
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[1]
folder=root/'outputs/raw-takes'
sources=[folder/name for name in ('09_rover_kayalar.mp4','09_rviz_kayalar.mp4','09_gazebo_kayalar.mp4')]
p=argparse.ArgumentParser();p.add_argument('--common-duration',action='store_true');args=p.parse_args()
out=root/('outputs/collage/rover_rviz_gazebo_30s.mp4' if args.common_duration else 'outputs/collage/rover_rviz_gazebo.mp4');out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise SystemExit('Existing collage preserved; select a new output before rerunning')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
records=[{'file':str(p.relative_to(root)),'sha256':digest(p),'duration_s':float(probe(p)['format']['duration'])} for p in sources]
duration=(min if args.common_duration else max)(r['duration_s'] for r in records)
cmd=['ffmpeg','-v','error','-n','-filter_complex_threads','1']
for p in sources:cmd+=['-i',str(p)]
filters=[]
for i in range(3):
 filters.append(f'[{i}:v]setpts=PTS-STARTPTS,scale=1024:720:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=1024:720:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=25,tpad=stop_mode=add:stop_duration={duration:.6f},trim=duration={duration:.6f}[v{i}]')
filters.append('[v0][v1][v2]hstack=inputs=3[out]')
cmd+=['-filter_complex',';'.join(filters),'-map','[out]','-an','-c:v','libx264','-threads','6','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
subprocess.run(cmd,check=True)
after=[digest(p) for p in sources]
if after!=[r['sha256'] for r in records]:raise RuntimeError('Source file changed during composition')
result=probe(out);video=next(s for s in result['streams'] if s['codec_type']=='video')
report={'created_at_utc':datetime.now(timezone.utc).isoformat(),'output':str(out.relative_to(root)),'sha256':digest(out),'sources':records,'source_files_unchanged':True,'left_to_right':['Unreal','RViz','Gazebo'],'composition':'Full clips start together for comparison; no claim of simultaneous recording. No cuts, speed change, crop, titles, music or added audio. Aspect ratios retained. Shorter clips are black after their original end; no loop/freeze. Output25fps duplicates frames as needed, without speeding playback.','duration_s':float(result['format']['duration']),'width':video['width'],'height':video['height']}
report['passed']=report['source_files_unchanged'] and abs(report['duration_s']-duration)<.1 and (video['width'],video['height'])==(3072,720)
if args.common_duration:report['composition']='30-second comparison of the existing source beginnings, not simultaneous footage. Sources unchanged; longer takes trimmed only in this derived preview. No added text/audio, no speed change, no looping. Gazebo render quality remains unsuitable for a final presentation.'
out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
