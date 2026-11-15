"""Collect existing observed tablet evidence; never substitutes for running checks."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[1]
    paths={
        'unreal_tests':'test-results/tablet-atlas-tests.json',
        'unreal_build':'test-results/tablet-atlas-build-source.json',
        'ros_build':'test-results/campaign-build-BaCr3yh2/ros-workspace.json',
        'atlas_stage':'test-results/tablet-atlas-stage.json',
        'rviz_transport':'test-results/tablet-atlas-rviz-transport/verification.json',
        'surface_saved_reload':'test-results/surface-v2-saved-scene.json',
        'campaign_flow':'test-results/tablet-science-flow/verification.json',
        'lab_flow':'test-results/tablet-lab-flow/verification.json',
        'visual':'test-results/tablet-atlas-visual.json',
    }
    records={}
    for name,path in paths.items():
        raw=(root/path).read_bytes();records[name]={'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'report':json.loads(raw)}
    native=records['unreal_tests']['report'];build=records['unreal_build']['report']
    source_matches=all((root/'unreal/Redline'/f['path'].replace('\\','/')).is_file() and hashlib.sha256((root/'unreal/Redline'/f['path'].replace('\\','/')).read_bytes()).hexdigest().lower()==f['sha256'].lower() for f in build['files'])
    checks={
        'native_tests':native['failed']==0 and native['notRun']==0 and native['succeeded']+native['succeededWithWarnings']>=32,
        'native_build_and_current_source':build['build_exit_code']==0 and build['source_snapshot_verified'] and source_matches,
        'ros_tests':'Summary: 161 tests, 0 errors, 0 failures, 0 skipped' in (root/'test-results/tablet-atlas-ros-build.stdout').read_text(),
        **{k:records[k]['report']['passed'] for k in ('atlas_stage','rviz_transport','surface_saved_reload','campaign_flow','lab_flow','visual')},
    }
    report={'schema':'redline.tablet.acceptance.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'passed':all(checks.values()),'checks':checks,
        'native_tests':{'success':native['succeeded'],'success_with_warnings':native['succeededWithWarnings'],'failed':native['failed']},
        'records':records,
        'credits':{'provider':'Tripo','generation':30,'conversion':5,'recorded_balance_after':345},
        'scope':'Handheld presentation, actual lossless RViz transport, currently implemented science/model products, atlas and saved v2 terrain collision.',
        'limits':[
            'Campaign integration human uses explicit SIMULATED teleport fixture; science is uncalibrated SCENARIO. Scout in that test was a stub; prior physical scout evidence remains separate.',
            'pH/conductivity are authored model results tied to real recorded simulated sample custody; no Gale/Phoenix measurement or oxide inference.',
            'Atlas stations/cards are a plan; distant human travel and all B1-B10 mission implementations are not enabled by selecting a card.',
            'Fast travel D022 is design only; safety/clock/pose authority integration and shelter acceptance remain open.',
            'Original scene/cache material differences retained in surface-v2-dependencies.json. Surface geometry acceptance is not final shader/FPS acceptance.',
            'Finger grip, cooked packaging, drone sensor perception, physical soil/contact/force measurements remain open.'
        ]}
    out=root/'docs/verification/TABLET_ACCEPTANCE.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'checks':checks,'path':str(out)},ensure_ascii=False))
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
