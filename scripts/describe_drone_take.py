"""Link the recorded viewport to observed flight phases; no invented route."""
import hashlib,json,math
from datetime import datetime,timedelta
from pathlib import Path
root=Path(__file__).resolve().parents[1];folder=root/'test-results/live-film-domain183';report=json.loads((folder/'observation.json').read_text());feed=folder/'actual-bridge.jsonl'
start=datetime.fromisoformat(report['created_at_utc'])-timedelta(seconds=report['elapsed_wall_s'])
shot=Path('/mnt/c/Users/USER/AppData/Local/Redline/LiveClips/02_drone_live-20261115T103244Z-5694DA0B/manifest.json');m=json.loads(shot.read_text());clipstart=datetime.fromisoformat(m['started_at_utc'].replace('Z','+00:00'));offset=(clipstart-start).total_seconds()
phases=[];last=None;points=[];observations={}
for line in feed.open(encoding='utf-8-sig'):
 r=json.loads(line);p=r['packet'];msg=p.get('msg',{});elapsed=r['elapsed_wall_s']
 if p.get('topic')=='/redline/campaign/state':
  s=json.loads(msg['data']).get('scout',{});phase=s.get('phase')
  if phase and phase!=last:phases.append({'phase':phase,'video_s_approx':round(elapsed-offset,1),'observer_wall_s':elapsed});last=phase
  if s.get('map_xyz_m'):points.append({'map_xyz_m':s['map_xyz_m'],'phase':phase,'video_s_approx':round(elapsed-offset,1)})
 elif p.get('topic')=='/redline/evidence':observations[msg['evidence_id']]=msg
active=[p for p in points if p['phase'] not in ('PARKED','COMPLETE','STOPPED')];home=[330.,-474.]
r={'video':'02_drone_ilk_ucus.mp4','source_feed':str(feed.relative_to(root)),'source_sha256':hashlib.sha256(feed.read_bytes()).hexdigest(),'timing_note':'Approximate video-relative phase times from observer end UTC minus its measured monotonic duration; scientific/physics clocks unchanged. Negative/over120 times lie outside clip.','video_duration_s':m['duration_wall_s'],'phases':phases,'authored_route_map_enu_m':[[330,-474],[354,-474],[354,-450],[330,-450]],'requested_altitude_m':20,'observed_max_home_distance_m':max(math.dist(p['map_xyz_m'][:2],home) for p in active),'observed_max_z_m':max(p['map_xyz_m'][2] for p in active),'complete_observed':any(p['phase']=='COMPLETE' for p in phases),'observed_evidence_count':len(observations),'map_status':'SCENARIO local ENU route on DERIVED BXW terrain','observation_status':'SIMULATED truth adapter, not camera reconstruction','quality':'PRE-STABILIZATION recording; final preferred flight still requires a retake'}
(root/'outputs/raw-takes/02_drone_aciklama.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='timing_note'},ensure_ascii=False))
