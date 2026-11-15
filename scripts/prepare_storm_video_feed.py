"""Select a wall-time window of the actual C1 capture; retain scientific clocks."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];src=root/'runs/20261115T105748Z-C1_SHOT-42/ue_feed.jsonl';out=root/'test-results/storm-video';out.mkdir(exist_ok=True)
records=[json.loads(s) for s in src.read_text().splitlines() if s.strip()];start,end=65.,185.;initial={};selected=[]
for r in records:
 t=r['_redline_elapsed_sec']
 if t<start:initial[r['topic']]=r
 elif t<=end:selected.append(r)
packet=[]
for r in initial.values():r=dict(r);r['_redline_elapsed_sec']=0.;packet.append(r)
for r in selected:r=dict(r);r['_redline_elapsed_sec']-=start;packet.append(r)
dst=out/'ue_feed.jsonl';dst.write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in packet))
(out/'source.json').write_text(json.dumps({'source':str(src.relative_to(root)),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'selected_wall_seconds':[start,end],'source_ros_timestamps_changed':False,'source_messages_changed':False,'mode':'RECORDED ROS PLAYBACK; no live commands','records':len(packet)},indent=2)+'\n')
