"""Geometry/physics registration checks; no claim of calibrated dynamics."""
import importlib.util
import json
import math
import copy
from pathlib import Path
import sys

import pytest

SCRIPTS=Path(__file__).parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('stage_delivered_rover',SCRIPTS/'stage_delivered_rover.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_delivered_geometry_moves_both_simulation_and_ros_joints(tmp_path):
    source=tmp_path/'asset';parts=source/'gazebo/parts';parts.mkdir(parents=True)
    (source/'textures').mkdir();(source/'textures/test.png').write_bytes(b'fixture')
    (source/'SOURCE.md').write_text('Synthetic test fixture, not NASA data')
    records=[]
    for name,pivot in [('Chassis',[.15,.02,1])]+[(f'wheel_0{n}_{side}',[x,y,.25])
            for n,x in ((1,1),(2,0),(3,-1)) for side,y in (('L',1),('R',-1))]:
        if name=='wheel_01_L':pivot[2]=.253  # art axle heights are not flight CAD
        filename='SM_'+name+'_LOD0'
        records.append({'source_name':name,'name':filename,'pivot_m':pivot})
        path=parts/filename.replace('_LOD0','_Gazebo.obj')
        path.write_text('v -0.25 -0.2 -0.25\nv 0.25 0.2 0.25\nf 1 2 1\n')
        path.with_suffix('.mtl').write_text('newmtl test\n')
    asset=source/'asset.json'
    asset.write_text(json.dumps({'master':{'unit':'metre','uniform_scale':1,
        'axes':'+X forward/+Y left/+Z up','handedness':'right'},'parts':records}))
    original={p:p.read_bytes() for p in source.rglob('*') if p.is_file()}
    out=tmp_path/'derived';geometry=m.stage(asset,out)
    sdf=m.ET.parse(out/'model.sdf');urdf=m.ET.parse(out/'rover_1.urdf')
    for name in ('fl','fr','ml','mr','rl','rr'):
        pose=list(map(float,sdf.find(f".//link[@name='wheel_{name}_link']/pose").text.split()))[:3]
        origin=list(map(float,urdf.find(f"joint[@name='wheel_{name}_suspension_joint']/origin").get('xyz').split()))
        assert pose==origin
        assert urdf.find(f"joint[@name='wheel_{name}_joint']/origin").get('xyz')=='0 0 0'
    assert len(sdf.findall(".//joint[@type='prismatic']"))==6
    for joint in sdf.findall(".//joint[@type='prismatic']"):
        assert joint.findtext('axis/xyz')=='0 0 1'
        assert float(joint.findtext('axis/dynamics/spring_stiffness'))>0
        assert float(joint.findtext('axis/limit/lower'))<0<float(joint.findtext('axis/limit/upper'))
    mass=sum(float(p.text) for p in sdf.findall('.//inertial/mass'))
    assert mass==pytest.approx(899)
    assert geometry['root_ground_clearance_m']==pytest.approx(.9995)
    wheel_z=[float(sdf.find(f".//link[@name='wheel_{n}_link']/pose").text.split()[2]) for n in ('fl','fr','ml','mr','rl','rr')]
    assert max(wheel_z)==min(wheel_z)
    # The art's zero-pose world height is preserved despite proxy levelling.
    for name,master_z in (('fl',.253),('fr',.25)):
        visual_z=float(sdf.find(f".//link[@name='wheel_{name}_link']/visual/pose").text.split()[2])
        assert wheel_z[0]+visual_z+1==pytest.approx(master_z)
    assert geometry['uniform_scale']==1
    assert geometry['root_in_asset_m']==[0,0,1]
    assert list(map(float,urdf.find("link[@name='rover_1/base_link']/inertial/origin").get('xyz').split()))==pytest.approx([.15,.02,0])
    assert float(sdf.find(".//link[@name='wheel_ml_link']/pose").text.split()[0])==0
    assert float(sdf.find(".//link[@name='wheel_mr_link']/pose").text.split()[0])==0
    assert geometry['wheel_drive_effort_nm']==pytest.approx(80*(899/144.4)*(.25/.28))
    for joint in sdf.findall(".//joint[@type='revolute']"):
        assert float(joint.findtext('axis/limit/effort'))==geometry['wheel_drive_effort_nm']
        child=joint.findtext('child')
        collision=sdf.find(f".//link[@name='{child}']/collision")
        roll=float(collision.findtext('pose').split()[3])
        assert -math.sin(roll)==pytest.approx(1)  # collision Z -> joint Y axle
        assert collision.findtext('surface/friction/ode/fdir1')=='0 1 0'
        assert collision.find('surface/friction/ode/fdir1').get('{'+m.GZ_NS+'}expressed_in')=='base_link'
        assert float(collision.findtext('surface/friction/ode/mu'))<float(collision.findtext('surface/friction/ode/mu2'))
        assert float(collision.findtext('surface/friction/ode/mu'))==geometry['wheel_friction']['lateral']
    assert all(p.read_bytes()==data for p,data in original.items())
    assert all(Path(item['derived']).is_file() for item in geometry['sources'])
    assert sdf.find('.//link[@name="base_link"]/visual/geometry/mesh/uri') is not None
    three_d=tmp_path/'derived_3d';m.stage(asset,three_d,lidar_3d=True)
    sensor=m.ET.parse(three_d/'model.sdf').find(".//sensor[@name='lidar_3d']")
    assert sensor.findtext('lidar/scan/vertical/samples')=='32'
    assert sensor.findtext('gz_frame_id')=='rover_1/lidar_link'
    config=json.loads((three_d/'perception.json').read_text())['/rover_1/ground_filter']['ros__parameters']
    assert config['expected_ground_z_m']==pytest.approx(-2.35+0.0005)
    with pytest.raises(ValueError,match='fresh'):m.stage(asset,out)


def test_navigation_envelope_and_inflation_cover_a_wide_extended_rover():
    params={name:{name:{'ros__parameters':{'footprint_padding':.05,'inflation_layer':{}}}}
            for name in ('local_costmap','global_costmap')}
    params['collision_monitor']={'ros__parameters':{'Stop':{},'Slow':{}}}
    params['controller_server']={'ros__parameters':{'FollowPath':{
        'vx_max':.4,'wz_max':.4,'ax_min':-.4,'model_dt':.05,'time_steps':56,
        'PathAngleCritic':{},'PathFollowCritic':{},'PathAlignCritic':{}},'progress_checker':{}}}
    params['planner_server']={'ros__parameters':{'GridBased':{}}}
    footprint=[[2.3,1.4],[2.3,-1.4],[-1.8,-1.4],[-1.8,1.4]]
    geometry={'footprint_m':footprint,'bounds_base_m':[[-1.8,-1.4,-.9],[2.3,1.4,1.3]]}
    baseline=copy.deepcopy(params);result=m.navigation_profile(params,geometry)
    for name in ('local_costmap','global_costmap'):
        grid=result[name][name]['ros__parameters']
        assert json.loads(grid['footprint'])==footprint
        assert grid['inflation_layer']['inflation_radius']>math.hypot(2.35,1.45)
    monitor=result['collision_monitor']['ros__parameters']
    global_grid=result['global_costmap']['global_costmap']['ros__parameters']
    assert global_grid['rolling_window']
    assert global_grid['resolution']==.2 and global_grid['width']==global_grid['height']==80
    assert result['planner_server']['ros__parameters']['GridBased']['minimum_turning_radius']==1.0
    assert result['planner_server']['ros__parameters']['GridBased']['smooth_path'] is False
    control=result['controller_server']['ros__parameters']['FollowPath']
    assert control['primary_controller']=='nav2_mppi_controller::MPPIController'
    assert control['rotate_to_heading_angular_vel']<=control['wz_max']
    assert control['closed_loop']
    assert result['controller_server']['ros__parameters']['progress_checker']['required_movement_angle']>0
    predicted_distance=control['time_steps']*control['model_dt']*control['vx_max']
    stopping_and_source_timeout=control['vx_max']**2/(2*abs(control['ax_min']))+.5*control['vx_max']
    assert predicted_distance>stopping_and_source_timeout
    assert control['PathFollowCritic']['offset_from_furthest']*(.2/math.hypot(2.3,1.4))>=.8
    assert control['time_steps']*control['model_dt']*control['vx_max']+2.3<10
    for name,margin in (('Stop',.2),('Slow',1)):
        polygon=json.loads(monitor[name]['points'])
        assert max(p[0] for p in polygon)==pytest.approx(2.3+margin)
        assert min(p[1] for p in polygon)==pytest.approx(-1.4-margin)
        assert monitor[name]['visualize']
    alternative=m.navigation_profile(baseline,geometry,controller_kind='rpp')['controller_server']['ros__parameters']['FollowPath']
    assert alternative['desired_linear_vel']<=.4
    assert alternative['use_collision_detection'] and alternative['max_allowed_time_to_collision_up_to_carrot']>0
    assert not alternative['allow_reversing']
    assert alternative['primary_controller'].endswith('RegulatedPurePursuitController')
