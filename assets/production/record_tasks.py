"""Read existing Tripo tasks and retain reproducible requests, never signed URLs."""
from pathlib import Path
import json,os,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
TASKS={
 'astronaut':['7583fea2-05ef-4340-8cc9-5b5a756d3eb4','2ddc3f89-aa39-4433-8651-bd8ea06a15a5','f43b5416-7d9d-4f96-8e36-66a31d3f58ad','0df6992f-5e0f-4687-8a32-524cdb69ca6e'],
 'rover_1':['310774f0-cd27-4265-8657-3c02c288e33d','089df3c5-f7e8-45c4-8072-8760fd8f6b2c'],
 'science_station':['d22a9e35-8dc4-4f79-a9a6-a3b7108c931c','c6235dab-3741-4b3f-9dc5-822f724df7f2'],
 'scout_1':['97e4e850-f1d3-4a62-8376-3d044bd3ac73'],
 'tool_apxs':['759649d6-e41f-4274-afbf-d93d718c8177'],
 'tool_libs':['c6ce5d78-a4cb-4265-8e9a-9110cfeb6f50'],
 'tool_drill':['a005625a-7eb4-4989-bc0e-50a30764a8aa','695a96a1-3728-4fc2-a536-c41fb26406fb'],
 'tool_neutron':['d1f56ecd-0f00-4164-9f46-0aac237d08a3'],
 'tool_multispectral':['1d1334b7-6e5f-4f38-b3ce-736803da0b83'],
}
out=ROOT/'production/tasks';out.mkdir(exist_ok=True)
records=[]
for aid,ids in TASKS.items():
    for task_id in ids:
        path=out/(task_id+'.json')
        if path.exists():record=json.loads(path.read_text())
        else:
            result=subprocess.run([shutil.which('tripo.cmd'),'task','get',task_id,'--json'],env=dict(os.environ,TRIPO_CLIENT_APP='codex'),capture_output=True,text=True,encoding='utf-8')
            if result.returncode:raise SystemExit(f'Read-only task lookup failed: {task_id}: {result.stderr}')
            raw=json.loads(result.stdout)
            record={key:raw[key] for key in ('task_id','type','status','progress','input','created_at','completed_at','credits_consumed') if key in raw}
            path.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        records.append({'asset_id':aid,'historical':task_id=='7583fea2-05ef-4340-8cc9-5b5a756d3eb4',**record})
        print('RECORDED',aid,task_id,record.get('credits_consumed'),flush=True)
prior=json.loads((ROOT/'incoming/scout_1/task.json').read_text())
records.append({'asset_id':'scout_1','historical':True,**{key:prior['task'][key] for key in ('task_id','type','status','input','created_at','completed_at','credits_consumed') if key in prior['task']}})
ledger={'opening_balance':930,'closing_balance':625,'frozen':0,'current_session_consumed':sum(float(x.get('credits_consumed',0)) for x in records if not x['historical']),'historical_consumed':sum(float(x.get('credits_consumed',0)) for x in records if x['historical']),'task_records':records,'failed_operations':[{'asset_id':'scout_1','step':'segment old task','result':'404 TASK_NOT_FOUND; local source retained','credits':0},{'asset_id':'scout_1','step':'upload original 44 MB GLB','result':'POST /v3/files timed out before task creation; balance unchanged; bounded 55k-triangle derivative used','credits':0}]}
(ROOT/'CREDIT_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
if ledger['current_session_consumed']!=305:raise SystemExit('Unexpected credit ledger total')
