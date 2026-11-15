import csv
import importlib.util
import json
import math
from pathlib import Path

spec=importlib.util.spec_from_file_location('verify_pose',Path(__file__).parents[1]/'t4_verify_pose.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_nonzero_origin_rotation_and_quaternion_sign_match_actual_actor(tmp_path):
    s=math.sqrt(.5);feed=tmp_path/'feed.jsonl';poses=tmp_path/'poses.csv'
    frames=[{'op':'publish','topic':'/redline/bridge/tf_static_snapshot','msg':{'transforms':[
        {'header':{'frame_id':'map'},'child_frame_id':'rover_1/odom','transform':{
            'translation':{'x':10,'y':20,'z':-3500},'rotation':{'x':0,'y':0,'z':s,'w':s}}}]}}]
    fields=['physics_stamp_sec','map_x_m','map_y_m','map_z_m','ue_x_cm','ue_y_cm','ue_z_cm','ue_qx','ue_qy','ue_qz','ue_qw']
    with poses.open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(fields)
        for stamp in range(10):
            frames.append({'op':'publish','topic':'/rover_1/odom','msg':{
                'header':{'frame_id':'rover_1/odom','stamp':{'sec':stamp,'nanosec':0}},'child_frame_id':'rover_1/base_link',
                'pose':{'pose':{'position':{'x':2,'y':3,'z':4},'orientation':{'x':0,'y':0,'z':0,'w':1}}}}})
            writer.writerow([stamp,7,22,-3496,700,-2200,-349600,0,0,s,-s])  # sign-equivalent UE quaternion
    feed.write_text('\n'.join(json.dumps(frame) for frame in frames))
    report=m.verify(feed,poses)
    assert report['passed'] and report['matched_samples']==10 and report['max_position_error_m']<1e-10
    poses.write_text(poses.read_text().replace('-2200','2200'))
    assert not m.verify(feed,poses)['passed']
