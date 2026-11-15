"""Freeze observed sensor success and failed route evidence separately."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil


def main():
    root=Path(__file__).resolve().parent.parent
    def evidence(relative):
        path=root/relative
        return {'path':str(relative),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    stationary=Path('test-results/t3-runtime-rBwIyXYE')
    result=json.loads((root/stationary/'result.json').read_text())
    sensor=json.loads((root/stationary/'perception-result.json').read_text())
    snapshots=[]
    for item in result['core_inputs']:
        if not item['snapshot'].endswith('/ground.py'):continue
        source=Path(item['snapshot'])
        if hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Core snapshot changed')
        destination=Path('docs/verification/source-metadata')/('T3_ground_'+item['sha256'][:12]+'.py')
        (root/destination).parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,root/destination);snapshots.append(evidence(destination))
    failures=[]
    for run in ('8O2IQ2ZF','vSXPwYoI','ayn453t9'):
        folder=Path('test-results')/('t3-runtime-'+run)
        nav=json.loads((root/folder/'navigation_result.json').read_text())
        runtime=json.loads((root/folder/'result.json').read_text())
        failures.append({'run':str(folder),'controller':runtime['controller_profile'],
            'started_at_utc':runtime['started_at_utc'],'passed':nav['passed'],'action_status':nav.get('action_status'),
            'physical_displacement_m':nav.get('measured_displacement_m'),'error':nav.get('error'),
            'evidence':[evidence(folder/name) for name in ('result.json','navigation_result.json','perception.log')]})
    report={'schema':'redline.t3.perception-commissioning.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'SIMULATED','stationary_low_object_detection_passed':sensor['passed'],
        'full_low_object_navigation_passed':False,'stationary_result':sensor,
        'stationary_runtime':str(stationary),'terrain':'Verified T1 BXW collision mesh',
        'fixture':'SCENARIO 1 x 1 x .4 m; centred 5 m forward on collision triangle, nominal .05 m embedded',
        'core_source_snapshots':snapshots,
        'evidence':[evidence(stationary/name) for name in ('result.json','perception-result.json','perception-result.npz',
                       'rover-geometry.json','nav2-delivered.yaml','bxw.sdf')],
        'failed_navigation_attempts':failures,
        'tests':{'ros_build':'test-results/t3-build-IsT2aCpf','records':76,'actual_cases':65,'ctest_wrappers':11,
                 'errors':0,'failures':0,'skipped':0,'pure_core_plus_geometry_cases':13,
                 'core_junit':evidence(Path('test-results/t3-ground-core.xml'))},
        'limits':['Low-object full navigation failed; profile is optional/experimental and does not replace the accepted 2D MPPI default.',
                  'Local observed plane patches and SCENARIO thresholds do not validate general terrain traversability, holes, cliffs or broad raised platforms.',
                  'Unknown return classifications are not certified free space; ground support can be occluded by the staged self envelope.',
                  'A single low box is not a natural-rock detection campaign.',
                  'Actual 50 Hz joint publication observed: 1240 joint samples alongside 124 raw 5 Hz clouds in ayn453t9.',
                  'Gazebo bounded shutdown required; process cleanliness is tracked separately.']}
    output=root/'docs/verification/T3_3D_PERCEPTION.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(output)


if __name__=='__main__':main()
