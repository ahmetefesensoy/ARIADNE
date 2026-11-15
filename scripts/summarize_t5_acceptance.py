"""Record bounded T5 technical evidence; do not infer T6 or full mission completion."""
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    build = read('test-results/t4-build-source.json')
    assert build['build_exit_code'] == 0
    ue_matches = all(digest(ROOT/'unreal/Redline'/f['path']) == f['sha256'].lower() for f in build['files'])
    ros = read('test-results/t5-build-jL2iSmSU/ros-workspace.json')
    ros_matches = all(digest(ROOT/'ros_ws/src'/f['path']) == f['sha256'].lower() for f in ros['files'])
    assert ue_matches and ros_matches, 'Source changed since the recorded builds; review current inputs first'
    automation = read('test-results/eva-final-automation/index.json')
    assert automation['succeeded'] == 20 and automation['failed'] == 0
    core = ET.parse(ROOT/'test-results/eva-intro-core.xml').getroot().find('testsuite')
    assert core is not None and core.attrib['failures'] == core.attrib['errors'] == '0'
    ros_log = (ROOT/'test-results/eva-intro-ros-build.log').read_text(encoding='utf-8-sig',errors='replace')
    assert 'Summary: 39 tests, 0 errors, 0 failures, 0 skipped' in ros_log
    runtime = (ROOT/'test-results/eva-final-game.log').read_text(encoding='utf-8-sig',errors='replace')
    motion = []
    for speed,clip,t,x,y,z in re.findall(r'EV1 runtime speed=([\d.]+) cm/s.*?anim=(\w+) time=([\d.]+) foot_l=\(([-\d.]+),([-\d.]+),([-\d.]+)\)', runtime):
        motion.append((float(speed),clip,float(t),float(x),float(y),float(z)))
    walk = [v for v in motion if v[1] == 'AN_Walk' and v[0] > 3]
    assert len(walk) > 1 and len({v[3:] for v in walk}) > 1, 'No observed moving walk-bone sequence'
    with (ROOT/'test-results/eva-final-unreal-pose.csv').open(encoding='utf-8-sig') as f:
        poses = list(csv.DictReader(f))
    periods = [float(b['wall_utc_s'])-float(a['wall_utc_s']) for a,b in zip(poses,poses[1:])]
    median_period = statistics.median(p for p in periods if p > 0)
    first, last = poses[0], poses[-1]
    displacement = math.hypot(float(last['map_x_m'])-float(first['map_x_m']), float(last['map_y_m'])-float(first['map_y_m']))
    assert displacement > 1 and median_period < .075
    capture = read('test-results/eva-final-live/capture.json')
    assert capture['passed']
    topics = defaultdict(list)
    for line in (ROOT/'test-results/eva-final-live/ue_feed.jsonl').read_text().splitlines():
        e = json.loads(line)
        topics[e['topic']].append(e['_redline_elapsed_sec'])
    assets = []
    for path in sorted((ROOT/'unreal/Redline/Content/EVAFixtures').rglob('*')):
        if path.suffix not in ('.uasset','.umap'): continue
        cached = Path(build['workspace'])/'Content/EVAFixtures'/path.relative_to(ROOT/'unreal/Redline/Content/EVAFixtures')
        assert digest(cached) == digest(path)
        assets.append({'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':digest(path),'bytes':path.stat().st_size})
    result = {
        'schema':'redline.t5.acceptance.v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
        'recorded_at_local':datetime.now().astimezone().isoformat(),
        'milestone':'T5','milestone_completed':True,
        'scope':'proje.md §18 technical EV1 walk + ROS FieldTile/RedLine + visible margin; final UI/science/whole narrative not accepted',
        'status':'SCENARIO human/suit/orientation, DERIVED BXW return field',
        'build':{'report':'test-results/t4-build-source.json','exit_code':0,'current_source_matches':ue_matches},
        'ros':{'report':'test-results/t5-build-jL2iSmSU/ros-workspace.json','tests':39,'errors':0,'failures':0,
               'current_source_matches':ros_matches,'workspace':ros['workspace']},
        'unreal_tests':{'report':'test-results/eva-final-automation/index.json','passed':20,'errors':0,'warnings':0,
                         'scope_note':'Full suite after skeleton/root conversion and input fixes; final later C++ edit changes interaction label text only, followed by successful build.'},
        'core_tests':{'report':'test-results/eva-intro-core.xml','passed':int(core.attrib['tests'])},
        'runtime':{'report':'test-results/eva-final-game.log','pose_csv':'test-results/eva-final-unreal-pose.csv',
                   'median_pose_publication_period_s':median_period,'median_publication_hz':1/median_period,
                   'observed_displacement_m':displacement,'moving_walk_samples':len(walk),
                   'observed_walk_max_speed_m_s':max(v[0] for v in walk)/100,
                   'bone_positions_changed':True,'idle_and_walk_present':{'AN_Idle','AN_Walk'}.issubset({v[1] for v in motion})},
        'live_capture':{'report':'test-results/eva-final-live/capture.json','passed':True,
                         'topic_counts':{k:len(v) for k,v in topics.items()},
                         'pose_span_s':max(topics['/crew/EV1/pose'])-min(topics['/crew/EV1/pose']),
                         'note':'Client was closed during capture; its pose span is shorter than the 35 s backend capture. This is not a 35 s continuous-pose claim.'},
        'render_review':{'method':'CUA live Unreal game screenshots','window_id':4983490,
            'observed':'Readable original light suit with red accents, human scale, idle/walk and movement, context station marker, return margin and north-up field/line map',
            'earlier_briefing_window_id':2558580,'briefing_E_to_TRAVERSE_observed':True,
            'full_manual_station_return_cycle_observed':False,'screenshot_file':None,
            'evidence_location':'CUA screenshots in conversation; no exported PNG'},
        'persistence':{'report':'test-results/eva-import-diagnosis.json','skeleton_and_material_reload':True,
                       'animation_scale_tests':'test-results/eva-repaired-animation-tests/index.json'},
        'authority':{'human':'Unreal','robot_physics_control':'ROS/Gazebo','return_field_rules':'ROS/redline_core',
                     'mission_phase':'ROS mission_manager; UE requests interaction only','PET':'sim_clock; independent of robot physics clock'},
        'open':['T6 S1 complete visual alarm/line shrink acceptance and SpaceWeather chart',
                'env/state visual integration, REMS and terrain horizon',
                'nominal PRECURSOR robot/science mission; orientation creates no science products',
                'full manual orientation out-and-back review, habitat interior, final UI and lighting polish',
                'T3 expanded low-obstacle 3D navigation acceptance'],
        'assets':assets,
    }
    out=ROOT/'docs/verification/T5_ACCEPTANCE.json'
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'milestone':'T5','technical_acceptance':True,'unreal_tests':20,'ros_tests':39,
                      'core_tests':int(core.attrib['tests']),'assets':len(assets),'pose_hz':1/median_period}))


if __name__ == '__main__':main()
