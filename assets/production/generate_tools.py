"""Run the exact saved Tripo plans once; --execute spends the authorized credits."""
from __future__ import annotations
import argparse,json,os,shutil,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('ids',nargs='*')
parser.add_argument('--execute',action='store_true')
args=parser.parse_args()
exe=shutil.which('tripo.cmd')
if not exe:raise SystemExit('tripo.cmd not found')
env=dict(os.environ,TRIPO_CLIENT_APP='codex')
for request in json.loads((ROOT/'production/tool_requests.json').read_text()):
    if args.ids and request['id'] not in args.ids:continue
    out=ROOT/'incoming'/request['id']/'tripo'
    if (out/'result.json').exists():
        print('ALREADY_DONE',request['id'],flush=True);continue
    base=[exe,'make',request['prompt'],'--model','H3.1','-p',f"face_limit={request['face_limit']}",'--seed',str(14112030+list(json.loads((ROOT/'production/tool_requests.json').read_text())).index(request)),'--out',str(out),'--name','redline-'+request['id'],'--json','--yes','--no-open']
    if request.get('parts'):
        base+=['-p','texture=false','-p','pbr=false','-p','generate_parts=true','--then','texture:pbr=true']
    else:base+=['-p','pbr=true']
    result=subprocess.run(base+['--dry-run'],env=env,text=True,capture_output=True,encoding='utf-8')
    plan=json.loads(result.stdout)
    if result.returncode or not plan.get('valid'):raise SystemExit(result.stdout+result.stderr)
    out.mkdir(parents=True,exist_ok=True)
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    print('PLAN',request['id'],plan['generation_credits_estimate'],flush=True)
    if not args.execute:continue
    # The normal CLI watch/download flow is used. A failed submit is never retried.
    result=subprocess.run(base,env=env,text=True,stdout=subprocess.PIPE,encoding='utf-8')
    if result.returncode:raise SystemExit(result.stdout)
    record=json.loads(result.stdout)
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    src=Path(record['model_file'])
    shutil.copy2(src,out.parent/'source.glb')
    print('DONE',request['id'],record.get('credits_consumed'),flush=True)
