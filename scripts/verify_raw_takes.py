import hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
root=Path('outputs/raw-takes');records=[]
for p in sorted(root.glob('*.mp4')):
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]));video=next(s for s in info['streams'] if s['codec_type']=='video')
 records.append({'file':str(p),'bytes':p.stat().st_size,'duration_s':float(info['format']['duration']),'width':video['width'],'height':video['height'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'passed':p.stat().st_size>1000 and float(info['format']['duration'])>1})
report={'created_at_utc':datetime.now(timezone.utc).isoformat(),'passed':bool(records) and all(r['passed'] for r in records),'files':records,'scope':'Uncut source exports only; no final edit, synchronised triple view or full mission acceptance.'}
Path('test-results/raw-recordings-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'files':len(records)}))
