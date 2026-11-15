#!/usr/bin/env python3
"""Freeze concise, hash-linked observed acceptance without changing raw runs."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parent.parent
    def evidence(path):
        source=root/path
        return {'path':str(path),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    runs={}
    for controller,run in (('mppi','JS5gnQtK'),('rpp','UpMtpiHd')):
        folder=Path('test-results')/('t3-runtime-'+run)
        result=json.loads((root/folder/'result.json').read_text())
        nav=json.loads((root/folder/'navigation_result.json').read_text())
        clearance=json.loads((root/folder/'clearance-analysis.json').read_text())
        build=Path('test-results')/('t3-build-dOTJEdcp' if controller=='mppi' else 't3-build-blH4VNZ8')
        runs[controller]={'status':'SIMULATED','started_at_utc':result['started_at_utc'],
            'ended_at_utc':result['ended_at_utc'],'passed_navigation':nav['passed'],'action_status':nav['action_status'],
            'physical_goal_error_m':nav['measured_goal_error_m'],'physical_displacement_m':nav['measured_displacement_m'],
            'estimated_goal_error_m':nav['goal_error_m'],'ground_height_residual_m':nav['measured_ground_contact_height_error_m'],
            'minimum_sampled_planar_clearance_m':clearance['minimum_sampled_planar_clearance_m'],
            'sampled_envelope_overlaps':clearance['envelope_overlap_samples'],
            'maximum_sample_gap_wall_s':clearance['maximum_sample_gap_wall_s'],
            'clean_shutdown':result['clean_shutdown'],'child_exit_diagnostics':result['child_exit_diagnostics'],
            'evidence':[evidence(folder/name) for name in ('result.json','navigation_result.json','clearance-analysis.json',
                         'physical-motion.json','perception.log','rover-geometry.json','nav2-delivered.yaml')]+[evidence(build/'ros-workspace.json')]}
    rotation=Path('test-results/t3-runtime-TiSy4OGe/rotation-result.json')
    report={'created_at_utc':datetime.now(timezone.utc).isoformat(),'schema':'redline.t3.obstacle-acceptance.v1',
        'rover':'NASA-derived delivered metre-scale visual; compliant skid-steer SCENARIO physics',
        'test_obstacle':'SCENARIO 1 x 1 x 3.5 m pillar 5 m ahead; sensed, not provided to planner as ground truth',
        'terrain':'T1-derived BXW physical mesh; static cost support 4 m, working costmap 0.2 m',
        'goal_source':'programmatic NavigateToPose; does not replace delivered-model RViz-click acceptance',
        'runs':runs,'rotation':{'result':json.loads((root/rotation).read_text()),'evidence':evidence(rotation)},
        'latest_build':{'path':'test-results/t3-build-y1iXPyWC','records':73,'actual_cases':63,'ctest_wrappers':10,
                        'failures':0,'errors':0,'skipped':0},
        'limits':['Single high commissioning obstacle; low-rock 3D detection is not validated by this acceptance.',
                  'Yaw-only sampled envelope check; gaps up to 8.7 s, not continuous collision proof.',
                  'Physics constants are SCENARIO; rocker-bogie, steering and terrain-contact calibration remain open.',
                  'Gazebo required bounded shutdown; phase passed and clean process shutdown are separate.',
                  'RPP run logged watchdog failure during shutdown; it is comparison evidence, not a safety claim.',
                  'New RViz visual acceptance is open: COPY MODE reappeared and the CUA capture returned the wrong surface.']}
    target=root/'docs/verification/T3_OBSTACLE_ACCEPTANCE.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(target)


if __name__=='__main__':main()
