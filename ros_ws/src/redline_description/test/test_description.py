import importlib.util
from pathlib import Path
import math

MODULE=Path(__file__).parents[1]/'scripts/generate_rover.py'
spec=importlib.util.spec_from_file_location('generate_rover',MODULE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_six_wheels_have_consistent_physical_and_ros_joints():
    sdf,urdf=module.generate();model=sdf.find('model')
    joints=[j for j in model.findall('joint') if j.get('type')=='revolute']
    assert len(joints)==6
    drive=next(p for p in model.findall('plugin') if p.get('name').endswith('DiffDrive'))
    assert len(drive.findall('left_joint'))==3 and len(drive.findall('right_joint'))==3
    for joint in joints:
        counterpart=urdf.find(f"joint[@name='{joint.get('name')}']")
        assert counterpart is not None
        assert joint.findtext('axis/xyz')==counterpart.find('axis').get('xyz')=='0 1 0'
    assert drive.findtext('tf_topic')!='/tf'
    publisher=next(p for p in model.findall('plugin') if p.get('name').endswith('JointStatePublisher'))
    assert publisher.findtext('update_rate')=='50'


def test_sensor_frames_exist_and_cameras_have_optical_transform():
    sdf,urdf=module.generate();frames={l.get('name') for l in urdf.findall('link')}
    sensors=sdf.findall('.//sensor');assert {s.get('type') for s in sensors}=={'camera','depth_camera','imu','gpu_lidar'}
    for sensor in sensors:assert sensor.findtext('gz_frame_id') in frames
    for name in ('camera_optical_frame','depth_optical_frame'):
        joint=urdf.find(f"joint[@name='{name}_fixed']")
        assert joint.find('origin').get('rpy')==f'{-math.pi/2} 0 {-math.pi/2}'


def test_mass_and_inertia_positive_no_collision_visual_art_coupling():
    sdf,_=module.generate()
    for link in sdf.findall('.//link'):
        assert float(link.findtext('inertial/mass'))>0
        assert all(float(link.findtext('inertial/inertia/'+axis))>0 for axis in ('ixx','iyy','izz'))
        assert link.find('collision/geometry') is not None
