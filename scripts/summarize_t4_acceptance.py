"""Freeze observed T4 milestone evidence and current build-source integrity."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parent.parent
    def read(path):return json.loads((root/path).read_text(encoding='utf-8-sig'))
    def evidence(path):
        source=root/path
        return {'path':path,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    build=read('test-results/t4-build-source.json')
    source_root=root/'unreal/Redline'
    expected={item['path'].replace('\\','/') for item in build['files']}
    excluded={'Binaries','Intermediate','Saved','DerivedDataCache','Content'}
    actual={p.relative_to(source_root).as_posix() for p in source_root.rglob('*')
            if p.is_file() and not excluded.intersection(p.relative_to(source_root).parts)}
    integrity=actual==expected and all(hashlib.sha256((source_root/item['path'].replace('\\','/')).read_bytes()).hexdigest().lower()==item['sha256'].lower() for item in build['files'])
    automation=read('test-results/t4-automation-guard9093/index.json')
    terrain=read('test-results/t4-terrain-import.json')
    live=read('test-results/t4-final-live-verification.json')
    offline=read('test-results/t4-final-offline-verification.json')
    capture=read('test-results/t4-final-live-capture.json')
    mock=read('test-results/t4-guard-mock9093.json')
    files=['test-results/t4-build-source.json','test-results/t4-automation-guard9093/index.json',
           'test-results/t4-guard-mock9093.json','test-results/t4-terrain-import.json','test-results/t4-content-artifacts.json',
           'test-results/t4-final-live-capture.json','test-results/t4-final-live-feed.jsonl','test-results/t4-final-live-pose.csv',
           'test-results/t4-final-live-verification.json','test-results/t4-final-offline-pose.csv','test-results/t4-live-feed7.jsonl',
           'test-results/t4-final-offline-verification.json','test-results/t4-direct-static-inspection.json','test-results/t4-python-final.xml',
           'scripts/t4_static_tf_snapshot.py','scripts/t4_bridge_runtime.py','scripts/t4_capture_feed.py','scripts/t4_verify_pose.py']
    report={'schema':'redline.t4.acceptance.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'milestone':'T4','complete_scope':'Spec section18 T4: fresh C++ bridge, imported terrain, coordinate automation and actual Unreal rover proxy at ROS-derived map pose',
        'milestone_complete':integrity and build['build_exit_code']==0 and automation['succeeded']==9 and automation['failed']==0
             and automation['notRun']==0 and automation['succeededWithWarnings']==0 and terrain['passed'] and live['passed'] and offline['passed'] and capture['passed'],
        'current_source_matches_built_inputs':integrity,'engine':terrain['engine'],
        'automation':{'succeeded':automation['succeeded'],'failed':automation['failed'],'warnings':automation['succeededWithWarnings'],
                      'not_run':automation['notRun'],'report_created_on_engine_utc':automation['reportCreatedOn']},
        'terrain':{'status':'DERIVED','meshes':len(terrain['meshes']),'triangle_total':sum(item['triangles'] for item in terrain['meshes']),
                   'native_complex_collision_checks':terrain['trace_checks'],'max_import_dimension_error_cm':max(item['max_dimension_error_cm'] for item in terrain['meshes']),
                   'source_policy':'Every technical terrain mesh reimported from the SHA-recorded FBX; no cached-UAsset extent-only attribution'},
        'live_pose':live,'offline_actor_replay':offline,
        'live_ros_runtime':'test-results/t3-runtime-5RZwQquS; full stationary ROS/Gazebo/Nav2 graph, no T4 motion commands',
        'static_snapshot_invalidation':'A conflicting or malformed status freezes the UE actor for this connection; later valid history cannot clear the latch. Tested in real isolated ROS and UE frame guard.',
        'transport_capture':{'topic_counts':capture['topic_counts'],'sent_operations':[op['op'] for op in capture['sent_operations']]},
        'reconnect_mock_events':mock['events'],
        'python_checks':{'transport_and_pose_unit_cases':3,'isolated_real_ros_static_snapshot_case':1,'static_snapshot_test_domain':84},
        'evidence':[evidence(path) for path in files],
        'limits':['Actual runtime actor tested under NullRHI; final visual design, rover mesh/rig and rendered UI are not included.',
                  'T4 live acceptance is a stationary pose comparison against ROS estimation, not independent localization truth or navigation acceptance.',
                  'Imported terrain is query-only; robot physics authority remains Gazebo/ROS.',
                  'Live and offline UE clients stopped at bounded test end; process shutdown is not separately certified.',
                  'WSL localhost forwarding failed in this session; local WSL private IP was verified. Resolve anew after WSL restart.',
                  'Static TF snapshot adapter is session-scoped; restart it with a new simulation run, and never use it as a second /tf publisher.',
                  'T5 overlays/EV1, T6 mission events, cooked packaging and full performance profiling are separate milestones.']}
    (root/'docs/verification/T4_ACCEPTANCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('milestone_complete','current_source_matches_built_inputs','automation')},indent=2))


if __name__=='__main__':main()
