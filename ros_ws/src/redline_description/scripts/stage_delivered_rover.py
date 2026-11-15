#!/usr/bin/env python3
"""Stage the user's metre-scale art on the spec's six-wheel fallback.

NASA/JPL-Caltech visual source notices are copied with the derived files.
This is SCENARIO passive wheel compliance/skid steering, not a flight model.
The source asset directory is read-only. No mesh generation or paid API calls.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from generate_rover import generate, tag, text_pose, box_inertia

GZ_NS='https://gazebosim.org/schemas'
ET.register_namespace('gz',GZ_NS)


def navigation_profile(params, geometry, *, controller_kind='mppi'):
    """Apply measured art envelope to both costmaps and collision polygons."""
    if controller_kind not in ('mppi','rpp'):raise ValueError('Unknown controller profile')
    footprint=geometry['footprint_m']
    # MPPI's SE2 collision shortcut requires inflation beyond the circumscribed
    # radius, including footprint padding. Derive it instead of hard-coding 2 m.
    radius=max(math.hypot(x,y) for x,y in footprint)
    for name in ('local_costmap','global_costmap'):
        grid=params[name][name]['ros__parameters']
        grid['footprint']=json.dumps(footprint)
        grid['inflation_layer']['inflation_radius']=radius+grid['footprint_padding']+.2
    params['local_costmap']['local_costmap']['ros__parameters'].update(width=20,height=20)
    # Keep the archive-derived slope map at its genuine 4 m support. A bounded
    # rolling master samples that layer and retains LiDAR obstacles at 20 cm;
    # painting a 1 m obstacle into 4 m master cells can block a valid departure.
    params['global_costmap']['global_costmap']['ros__parameters'].update(
        rolling_window=True,width=80,height=80,resolution=.2)
    controller=params['controller_server']['ros__parameters']['FollowPath']
    # Keep the 56 x .05 s receding horizon. Full-footprint collision checking
    # already includes the front overhang at every predicted centre pose.
    # Extending centre travel by the body length counted that extent twice.
    controller['PathAngleCritic']['max_angle_to_furthest']=.35
    controller.update(plugin='nav2_rotation_shim_controller::RotationShimController',
                      primary_controller='nav2_mppi_controller::MPPIController',
                      angular_dist_threshold=.35,angular_disengage_threshold=.15,
                      forward_sampling_distance=1.0,rotate_to_heading_angular_vel=.3,
                      max_angular_accel=.4,simulate_ahead_time=1.0,
                      closed_loop=True,rotate_to_goal_heading=True)
    progress=params['controller_server']['ros__parameters']['progress_checker']
    progress.update(plugin='nav2_controller::PoseProgressChecker',required_movement_angle=.1)
    # The old 4 m radius was forced by the coarse search grid, not measured
    # vehicle geometry. Match this fallback profile's full-speed v/omega limit.
    planner=params['planner_server']['ros__parameters']['GridBased']
    planner['minimum_turning_radius']=controller['vx_max']/controller['wz_max']
    # Smac's optional smoother checks centre costs; the strict full-envelope
    # post-check observed a smoothed corner hitting the pillar. Retain the
    # unsmoothed SE2 lattice route and its intermediate collision checks.
    planner['smooth_path']=False
    # Densification also bounds corner travel during rotation. For a large
    # footprint on a 1 m radius, four samples no longer mean 0.8 metres.
    step=planner.get('densification_step',.2)
    curved_step=min(step,step*planner['minimum_turning_radius']/radius)
    offset=math.ceil(.8/curved_step)
    for critic in ('PathFollowCritic','PathAngleCritic','PathAlignCritic'):
        controller[critic]['offset_from_furthest']=offset
    monitor=params['collision_monitor']['ros__parameters']
    low,high=geometry['bounds_base_m']
    for name,margin in (('Stop',.2),('Slow',1.0)):
        monitor[name]['points']=json.dumps([[high[0]+margin,high[1]+margin],[high[0]+margin,low[1]-margin],
                                           [low[0]-margin,low[1]-margin],[low[0]-margin,high[1]+margin]])
        monitor[name].update(visualize=True,polygon_pub_topic='collision_'+name.lower())
    monitor['Slow'].update(action_type='limit',linear_limit=.3*controller['vx_max'],angular_limit=.3*controller['wz_max'])
    monitor['Slow'].pop('slowdown_ratio',None)
    if controller_kind=='rpp':
        # Explicit diagnostic alternative. The v3 MPPI profile stays default.
        params['controller_server']['ros__parameters']['FollowPath']={
            'plugin':'nav2_rotation_shim_controller::RotationShimController',
            'primary_controller':'nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController',
            'angular_dist_threshold':.35,'angular_disengage_threshold':.15,
            'forward_sampling_distance':1.0,'rotate_to_heading_angular_vel':.3,
            'max_angular_accel':.4,'simulate_ahead_time':1.0,'closed_loop':True,
            'rotate_to_goal_heading':True,'desired_linear_vel':.3,
            'lookahead_dist':.8,'min_lookahead_dist':.6,'max_lookahead_dist':1.2,
            'use_velocity_scaled_lookahead_dist':False,'transform_tolerance':.2,
            'min_approach_linear_velocity':.05,'approach_velocity_scaling_dist':1.0,
            'max_allowed_time_to_collision_up_to_carrot':1.5,'use_collision_detection':True,
            'use_regulated_linear_velocity_scaling':True,'regulated_linear_scaling_min_radius':1.0,
            'regulated_linear_scaling_min_speed':.03,'use_cost_regulated_linear_velocity_scaling':False,
            'use_rotate_to_heading':False,'allow_reversing':False,'stateful':True}
    return params


def vertices(path):
    with path.open() as stream:
        return [tuple(map(float, line.split()[1:4])) for line in stream if line.startswith('v ')]


def stage(asset_path, out, *, lidar_3d=False):
    asset_path=Path(asset_path).resolve();out=Path(out).resolve()
    if out.exists():
        raise ValueError('Choose a fresh derived output directory')
    asset_bytes=asset_path.read_bytes();asset=json.loads(asset_bytes)
    if asset['master']['unit']!='metre' or asset['master']['uniform_scale']!=1.0:
        raise ValueError('Expected delivered metre-scale master at uniform scale 1')
    if asset['master']['axes']!='+X forward/+Y left/+Z up' or asset['master']['handedness']!='right':
        raise ValueError('Expected delivered right-handed ROS master axes')
    parts={p['source_name']:p for p in asset['parts']}
    wheel_parts={f'wheel_{position}{side}':parts[f'wheel_0{number}_{side.upper()}']
                 for position,number in (('f',1),('m',2),('r',3)) for side in ('l','r')}
    wheel_plane=sum(p['pivot_m'][2] for p in wheel_parts.values())/6
    # DiffDrive odometry describes the middle axle, not the art chassis pivot.
    # Put base_link over that axle; retain the art chassis height. Keeping the
    # previous 14.4 cm longitudinal offset creates false translation on turns.
    root=list(parts['Chassis']['pivot_m'])
    root[:2]=[sum(wheel_parts[name]['pivot_m'][i] for name in ('wheel_ml','wheel_mr'))/2 for i in (0,1)]
    sdf,urdf=generate();model=sdf.find('model');base=model.find("link[@name='base_link']")
    fixture_mass=sum(float(link.findtext('inertial/mass')) for link in model.findall('link'))
    fixture_radius=float(model.find("link[@name='wheel_fl_link']/collision/geometry/cylinder/radius").text)
    fixture_effort=float(model.find("joint[@name='wheel_fl_joint']/axis/limit/effort").text)
    ubase=urdf.find("link[@name='rover_1/base_link']")
    for parent in (base,ubase):
        for visual in parent.findall('visual'):parent.remove(visual)
    sources=[];bounds=[]
    wheel_names={p['source_name']:name for name,p in wheel_parts.items()}
    for part in asset['parts']:
        source=asset_path.parent/'gazebo/parts'/part['name'].replace('_LOD0','_Gazebo.obj')
        points=vertices(source)
        if not points:raise ValueError(f'Empty mesh: {source}')
        destination=out/'gazebo/parts'/source.name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        sources.append({'source':str(source),'sha256':digest,'derived':str(destination)})
        material=source.with_suffix('.mtl')
        shutil.copyfile(material,destination.with_suffix('.mtl'))
        sources.append({'source':str(material),'sha256':hashlib.sha256(material.read_bytes()).hexdigest(),
                        'derived':str(destination.with_suffix('.mtl'))})
        bounds.extend(tuple(v[i]+part['pivot_m'][i]-root[i] for i in range(3)) for v in points)
        wheel=wheel_names.get(part['source_name'])
        sparent=model.find(f"link[@name='{wheel}_link']") if wheel else base
        uparent=urdf.find(f"link[@name='rover_1/{wheel}_link']") if wheel else ubase
        if wheel:
            for parent in (sparent,uparent):
                for visual in parent.findall('visual'):parent.remove(visual)
        xyz=(0,0,part['pivot_m'][2]-wheel_plane) if wheel else tuple(part['pivot_m'][i]-root[i] for i in range(3))
        visual=tag(sparent,'visual',name=part['name']);tag(visual,'pose',text_pose((*xyz,0,0,0)))
        tag(tag(tag(visual,'geometry'),'mesh'),'uri',destination.as_uri())
        visual=tag(uparent,'visual');tag(visual,'origin',xyz=text_pose(xyz))
        tag(tag(visual,'geometry'),'mesh',filename=destination.as_uri())
    # Nominal rolling cylinders, rather than polygonal art grousers, own contact.
    radius=.25;width=.4;wheel_mass=10.0;sensor_mass=.4;total_mass=899.0
    lateral_friction=.5
    suspension_mass=1.0
    # Preserve the fallback's mass/radius-normalized actuator ceiling. On the
    # uneven DEM a few loaded wheels must overcome lateral skid resistance;
    # the inherited 80 Nm ceiling was verified insufficient there. This is
    # SCENARIO actuator sizing, not measured MSL motor performance.
    drive_effort=fixture_effort*(total_mass/fixture_mass)*(radius/fixture_radius)
    for name,part in wheel_parts.items():
        xyz=tuple(part['pivot_m'][i]-root[i] for i in range(3))
        # The delivered art has up to 2.9 mm axle-height differences. A rigid
        # fallback cannot follow those without loading only diagonal wheels.
        # Level physical axle centres; offset the art to preserve its zero pose.
        xyz=(xyz[0],xyz[1],wheel_plane-root[2])
        link=model.find(f"link[@name='{name}_link']");link.find('pose').text=text_pose((*xyz,0,0,0))
        link.find('inertial/mass').text=str(wheel_mass)
        moments=(wheel_mass*(3*radius**2+width**2)/12,wheel_mass*radius**2/2,wheel_mass*(3*radius**2+width**2)/12)
        for axis,value in zip(('ixx','iyy','izz'),moments):link.find('inertial/inertia/'+axis).text=str(value)
        link.find('collision/geometry/cylinder/radius').text=str(radius)
        link.find('collision/geometry/cylinder/length').text=str(width)
        # DART's explicit frame extension keeps the lateral friction direction
        # on the chassis +Y, independent of wheel roll/collision rotation.
        # These directional coefficients are SCENARIO, not Martian soil data.
        friction=link.find('collision/surface/friction/ode')
        friction.find('mu').text=str(lateral_friction);friction.find('mu2').text='1.0'
        direction=tag(friction,'fdir1','0 1 0');direction.set('{'+GZ_NS+'}expressed_in','base_link')
        urdf.find(f"joint[@name='{name}_joint']/origin").set('xyz',text_pose(xyz))
        model.find(f"joint[@name='{name}_joint']/axis/limit/effort").text=str(drive_effort)
        # Explicit SCENARIO vertical compliance for the rigid fallback. Without
        # it, a 1 m DEM mesh can unload four wheels and invalidate wheel odometry.
        # This is not the NASA rocker/bogie mechanism or flight suspension data.
        hub_name=name+'_carrier';hub=tag(model,'link',name=hub_name)
        tag(hub,'pose',text_pose((*xyz,0,0,0)))
        inertial=tag(hub,'inertial');tag(inertial,'mass',suspension_mass)
        inertia=tag(inertial,'inertia')
        for key in ('ixx','iyy','izz'):tag(inertia,key,.001)
        for key in ('ixy','ixz','iyz'):tag(inertia,key,0)
        suspension_name=name+'_suspension_joint'
        joint=tag(model,'joint',name=suspension_name,type='prismatic')
        tag(joint,'parent','base_link');tag(joint,'child',hub_name)
        axis=tag(joint,'axis');tag(axis,'xyz','0 0 1')
        limit=tag(axis,'limit')
        for key,value in (('lower',-.08),('upper',.12),('effort',5000),('velocity',1)):tag(limit,key,value)
        dynamics=tag(axis,'dynamics')
        for key,value in (('spring_reference',0),('spring_stiffness',10000),('damping',1000)):tag(dynamics,key,value)
        model.find(f"joint[@name='{name}_joint']/parent").text=hub_name
        tag(urdf,'link',name='rover_1/'+hub_name)
        uj=tag(urdf,'joint',name=suspension_name,type='prismatic')
        tag(uj,'parent',link='rover_1/base_link');tag(uj,'child',link='rover_1/'+hub_name)
        tag(uj,'origin',xyz=text_pose(xyz));tag(uj,'axis',xyz='0 0 1')
        tag(uj,'limit',lower='-.08',upper='.12',effort='5000',velocity='1')
        urdf.find(f"joint[@name='{name}_joint']/parent").set('link','rover_1/'+hub_name)
        urdf.find(f"joint[@name='{name}_joint']/origin").set('xyz','0 0 0')
        jsp=next(p for p in model.findall('plugin') if p.get('name').endswith('JointStatePublisher'))
        tag(jsp,'joint_name',suspension_name)
    chassis_source=asset_path.parent/'gazebo/parts'/parts['Chassis']['name'].replace('_LOD0','_Gazebo.obj')
    chassis=vertices(chassis_source)
    low=[min(p[i] for p in chassis) for i in range(3)];high=[max(p[i] for p in chassis) for i in range(3)]
    size=[high[i]-low[i] for i in range(3)]
    com=[parts['Chassis']['pivot_m'][i]-root[i] for i in range(3)]
    center=[(low[i]+high[i])/2+com[i] for i in range(3)]
    base.find('collision/geometry/box/size').text=text_pose(size)
    tag(base.find('collision'),'pose',text_pose((*center,0,0,0)))
    mass=total_mass-6*(wheel_mass+suspension_mass)-sensor_mass
    for parent in (base,ubase):
        mass_node=parent.find('inertial/mass')
        if parent is base:mass_node.text=str(mass)
        else:mass_node.set('value',str(mass))
        for axis,value in zip(('ixx','iyy','izz'),box_inertia(mass,size)):
            if parent is base:parent.find('inertial/inertia/'+axis).text=str(value)
            else:parent.find('inertial/inertia').set(axis,str(value))
    tag(base.find('inertial'),'pose',text_pose((*com,0,0,0)))
    tag(ubase.find('inertial'),'origin',xyz=text_pose(com))
    # Keep sensors clear of the delivered art. This high 2D scan cannot detect
    # low rocks; a 3D ground-separation pipeline is a separate acceptance gate.
    sensor_master={'lidar_link':(root[0],0,2.35),'camera_link':(.75,-.25,2.12),
                   'depth_link':(.75,-.13,2.12),'imu_link':tuple(root)}
    for name,master_xyz in sensor_master.items():
        xyz=tuple(master_xyz[i]-root[i] for i in range(3))
        model.find(f"link[@name='{name}']/pose").text=text_pose((*xyz,0,0,0))
        urdf.find(f"joint[@name='{name}_fixed']/origin").set('xyz',text_pose(xyz))
    drive=next(p for p in model.findall('plugin') if p.get('name').endswith('DiffDrive'))
    track=sum(abs(p['pivot_m'][1]) for p in wheel_parts.values())/3
    drive.find('wheel_separation').text=str(track);drive.find('wheel_radius').text=str(radius)
    lo=[min(v[i] for v in bounds) for i in range(3)];hi=[max(v[i] for v in bounds) for i in range(3)]
    # Include the preserved posed arm in the navigation footprint.
    footprint=[[hi[0],hi[1]],[hi[0],lo[1]],[lo[0],lo[1]],[lo[0],hi[1]]]
    clearance=sum(root[2]-p['pivot_m'][2]+radius for p in wheel_parts.values())/6
    sensor_offset=[sensor_master['lidar_link'][i]-root[i] for i in range(3)]
    if lidar_3d:
        lidar_link=model.find("link[@name='lidar_link']")
        sensor=copy.deepcopy(lidar_link.find('sensor'))
        sensor.set('name','lidar_3d');sensor.find('topic').text='/rover_1/lidar_3d'
        sensor.find('update_rate').text='5'
        vertical=tag(sensor.find('lidar/scan'),'vertical')
        for key,value in (('samples',32),('resolution',1),('min_angle',-.95),('max_angle',.1)):tag(vertical,key,value)
        lidar_link.append(sensor)
    for tree,path in ((sdf,out/'model.sdf'),(urdf,out/'rover_1.urdf')):
        ET.indent(tree);ET.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
    shutil.copyfile(asset_path.parent/'SOURCE.md',out/'SOURCE.md')
    shutil.copytree(asset_path.parent/'textures',out/'textures')
    for source in sorted((asset_path.parent/'textures').rglob('*')):
        if source.is_file():sources.append({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                                           'derived':str(out/'textures'/source.relative_to(asset_path.parent/'textures'))})
    if asset_path.read_bytes()!=asset_bytes:raise ValueError('Asset metadata changed during staging')
    for item in sources:
        if any(hashlib.sha256(Path(item[key]).read_bytes()).hexdigest()!=item['sha256'] for key in ('source','derived')):
            raise ValueError('Source/derived asset changed during staging')
    geometry={'status':'SCENARIO','asset_sha256':hashlib.sha256(asset_bytes).hexdigest(),
        'uniform_scale':1.0,'root_in_asset_m':root,'radius_m':radius,'wheel_width_m':width,
        'root_frame_basis':'middle axle XY, art chassis Z; nominal SCENARIO COM remains at chassis pivot',
        'track_m':track,'total_mass_kg':total_mass,'base_mass_kg':mass,'body_size_m':size,
        'wheel_drive_effort_nm':drive_effort,'drive_effort_basis':'SCENARIO fixture ceiling scaled by total mass and rolling radius; not an MSL motor measurement',
        'wheel_friction':{'lateral':lateral_friction,'longitudinal':1.0,'fdir1':'0 1 0','frame':'base_link','status':'SCENARIO'},
        'wheel_plane_master_z_m':wheel_plane,
        'max_wheel_level_adjustment_m':max(abs(p['pivot_m'][2]-wheel_plane) for p in wheel_parts.values()),
        'suspension':{'status':'SCENARIO','type':'six independent passive vertical carriers, not rocker bogie',
                      'travel_m':[-.08,.12],'spring_stiffness_npm':10000,'damping_nspm':1000,'carrier_mass_kg':suspension_mass},
        'root_ground_clearance_m':clearance,'footprint_m':footprint,'bounds_base_m':[lo,hi],
        'lidar_3d':lidar_3d,'lidar_offset_base_m':sensor_offset,
        'sources':sources,'source_files_modified':False,
        'physics':'six-wheel compliant skid-steer fallback, not Curiosity rocker bogie',
        'limits':['Mass partition, inertia and friction are uncalibrated SCENARIO assumptions.',
                  'Chassis box and six rolling cylinders are collision proxies; arm/mast collision is not modeled.',
                  'Art zero pose is preserved; steering and suspension arm art are fixed while wheel carriers move vertically.',
                  'High single-plane 2D LiDAR does not establish low-rock detection or 3D ground separation.']}
    (out/'geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
    if lidar_3d:
        parameters={'use_sim_time':True,'frame':'rover_1/lidar_link',
            'expected_ground_z_m':-(clearance+sensor_offset[2]),
            'self_bounds':[lo[i]-sensor_offset[i]-.04 for i in range(3)]+[hi[i]-sensor_offset[i]+.04 for i in range(3)]}
        (out/'perception.json').write_text(json.dumps({'/rover_1/ground_filter':{'ros__parameters':parameters}},indent=2)+'\n')
    return geometry


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--nav-config',type=Path)
    parser.add_argument('--controller',choices=['mppi','rpp'],default='mppi')
    parser.add_argument('--lidar-3d',action='store_true')
    args=parser.parse_args();result=stage(args.asset,args.out,lidar_3d=args.lidar_3d)
    if args.nav_config:
        import yaml
        params=navigation_profile(yaml.safe_load(args.nav_config.read_text()),result,controller_kind=args.controller)
        if args.lidar_3d:
            for grid_name in ('local_costmap','global_costmap'):
                layer=params[grid_name][grid_name]['ros__parameters']['obstacle_layer']
                layer.update(observation_sources='cloud ground',min_obstacle_height=-10000.,max_obstacle_height=10000.)
                layer['cloud']={'topic':'/rover_1/lidar/obstacles','data_type':'PointCloud2',
                    'marking':True,'clearing':False,'min_obstacle_height':-10000.,'max_obstacle_height':10000.,
                    'obstacle_max_range':8.,'obstacle_min_range':.15,'expected_update_rate':.5}
                layer['ground']={'topic':'/rover_1/lidar/ground','data_type':'PointCloud2',
                    'marking':False,'clearing':True,'min_obstacle_height':-10000.,'max_obstacle_height':10000.,
                    'raytrace_max_range':8.,'raytrace_min_range':.15,'expected_update_rate':.5}
            monitor=params['collision_monitor']['ros__parameters']
            monitor['observation_sources']=['scan','cloud']
            monitor['cloud']={'type':'pointcloud','topic':'/rover_1/lidar/obstacles',
                'min_height':-2.,'max_height':3.,'enabled':True,'source_timeout':.5}
        (args.out/'nav2.yaml').write_text(yaml.safe_dump(params,sort_keys=False))
    print(json.dumps({k:v for k,v in result.items() if k!='sources'},indent=2))
