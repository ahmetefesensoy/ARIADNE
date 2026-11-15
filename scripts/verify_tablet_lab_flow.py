"""Verify optional remote lab from an actual completed campaign custody record."""
import asyncio,json,math,time,argparse
from pathlib import Path
import websockets
async def run(args):
    args.out.mkdir(parents=True,exist_ok=True);start=time.monotonic();latest=None;response=None;original=None
    async with websockets.connect(args.url,max_size=500000) as ws:
        await ws.send(json.dumps({'op':'subscribe','topic':'/redline/campaign/state','type':'std_msgs/msg/String','throttle_rate':100}))
        sent=False
        while time.monotonic()-start<240:
            envelope=json.loads(await asyncio.wait_for(ws.recv(),10))
            if envelope.get('op')=='service_response':response=envelope
            if envelope.get('topic')=='/redline/campaign/state':
                latest=json.loads(envelope['msg']['data'])
                ready=[s for s in latest['samples'] if s['state']==7 and s['container_id']]
                if ready and latest.get('done') and not sent:
                    original=dict(ready[0]);sent=True
                    await ws.send(json.dumps({'op':'call_service','id':'verify-lab','service':'/redline/science/analyze_sample','type':'redline_msgs/srv/AnalyzeSample',
                        'args':{'request_id':'verify-tablet-lab-'+str(int(time.time())),'sample_id':original['sample_id'],'method':'WCL_SCENARIO','integration_s':120.}}))
                products=[p for p in latest['products'] if p['instrument']=='WCL_SCENARIO']
                if products:
                    p=products[-1];series=p['summary']['series'];path=Path(p['payload_uri'])
                    checks={'accepted_then_result':bool(response and response['values']['accepted']),
                       'persisted_json_xml':path.is_file() and path.with_suffix('.xml').is_file(),
                       'simulated_model':p['status']==2 and p['summary']['model_only'],
                       'ph_series':len(series['ph'])==len(series['time_s'])==31 and all(math.isfinite(v) and 0<=v<=14 for v in series['ph']),
                       'ec_series':len(series['conductivity_ms_cm'])==31,
                       'custody_preserved':next(s for s in latest['samples'] if s['sample_id']==original['sample_id'])==original}
                    report={'passed':all(checks.values()),'checks':checks,'product':p,'run_id':latest['run_id'],
                            'source':'actual prior campaign sample custody + actual ROS AnalyzeSample service and persisted model product',
                            'limitation':'human of campaign test is explicit simulated pose fixture; pH and conductivity are authored model, not NASA measurements'}
                    (args.out/'verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
                    print(json.dumps({'passed':report['passed'],'checks':checks},ensure_ascii=False));return 0 if report['passed'] else 1
    raise TimeoutError('actual lab product not received')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--out',required=True,type=Path)
    raise SystemExit(asyncio.run(run(p.parse_args())))
