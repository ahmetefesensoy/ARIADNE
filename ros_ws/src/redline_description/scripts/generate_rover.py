#!/usr/bin/env python3
"""One SCENARIO geometry source for Gazebo physics and ROS robot frames.

Primitive visuals are integration fixtures; final user meshes can replace the
visual elements without changing physical joints, sensors or frame ownership.
This is a simplified skid-steer six-wheel vehicle, not Curiosity's suspension.
"""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

RADIUS = .28
WIDTH = .18
TRACK = 1.25
WHEEL_X = (.7, 0, -.7)
WHEEL_Z = -.22
BODY_SIZE = (1.7, 1.0, .32)
BODY_MASS = 120.0
SENSORS = {'lidar_link': (0,0,.65), 'camera_link': (.45,0,.52),
           'depth_link': (.45,.12,.52), 'imu_link': (0,0,0)}


def tag(parent, element, text=None, **attrs):
    node = ET.SubElement(parent,element,attrs)
    if text is not None: node.text = str(text)
    return node


def text_pose(values):
    return ' '.join(f'{v:.12g}' for v in values)


def box_inertia(mass, size):
    x,y,z=size
    return (mass*(y*y+z*z)/12, mass*(x*x+z*z)/12, mass*(x*x+y*y)/12)


def add_sdf_link(model,name,xyz,mass,size=None,wheel=False):
    link=tag(model,'link',name=name)
    tag(link,'pose',text_pose((*xyz,0,0,0)))
    inertial=tag(link,'inertial');tag(inertial,'mass',mass)
    inertia=tag(inertial,'inertia')
    moments=box_inertia(mass,size) if size else (mass*(3*RADIUS**2+WIDTH**2)/12,mass*RADIUS**2/2,mass*(3*RADIUS**2+WIDTH**2)/12)
    for key,value in zip(('ixx','iyy','izz'),moments):tag(inertia,key,value)
    for key in ('ixy','ixz','iyz'):tag(inertia,key,0)
    for kind in ('visual','collision'):
        element=tag(link,kind,name=f'{name}_{kind}')
        geometry=tag(element,'geometry')
        if wheel:
            tag(element,'pose',f'0 0 0 {-math.pi/2} 0 0')
            cylinder=tag(geometry,'cylinder');tag(cylinder,'radius',RADIUS);tag(cylinder,'length',WIDTH)
        else:tag(tag(geometry,'box'),'size',text_pose(size))
        if kind=='collision':
            ode=tag(tag(tag(element,'surface'),'friction'),'ode')
            tag(ode,'mu',1.0);tag(ode,'mu2',1.0)
        else:
            mat=tag(element,'material');tag(mat,'ambient','.35 .35 .35 1');tag(mat,'diffuse','.55 .55 .55 1')
    return link


def generate():
    sdf=ET.Element('sdf',version='1.9');model=tag(sdf,'model',name='rover_1')
    add_sdf_link(model,'base_link',(0,0,0),BODY_MASS,BODY_SIZE)
    urdf=ET.Element('robot',name='rover_1')
    base=tag(urdf,'link',name='rover_1/base_link')
    inertial=tag(base,'inertial');tag(inertial,'mass',value=str(BODY_MASS))
    moments=box_inertia(BODY_MASS,BODY_SIZE)
    tag(inertial,'inertia',ixx=str(moments[0]),iyy=str(moments[1]),izz=str(moments[2]),ixy='0',ixz='0',iyz='0')
    tag(tag(tag(base,'visual'),'geometry'),'box',size=text_pose(BODY_SIZE))
    joints=[]
    for side,y in (('l',TRACK/2),('r',-TRACK/2)):
        for position,x in zip(('f','m','r'),WHEEL_X):
            name=f'wheel_{position}{side}'
            add_sdf_link(model,name+'_link',(x,y,WHEEL_Z),4,wheel=True)
            joint=tag(model,'joint',name=name+'_joint',type='revolute')
            tag(joint,'parent','base_link');tag(joint,'child',name+'_link')
            axis=tag(joint,'axis');tag(axis,'xyz','0 1 0')
            limit=tag(axis,'limit');tag(limit,'lower',-1e16);tag(limit,'upper',1e16);tag(limit,'effort',80);tag(limit,'velocity',6)
            tag(tag(axis,'dynamics'),'damping',.05)
            link=tag(urdf,'link',name='rover_1/'+name+'_link')
            visual=tag(link,'visual');tag(visual,'origin',rpy=f'{-math.pi/2} 0 0')
            tag(tag(visual,'geometry'),'cylinder',radius=str(RADIUS),length=str(WIDTH))
            uj=tag(urdf,'joint',name=name+'_joint',type='continuous')
            tag(uj,'parent',link='rover_1/base_link');tag(uj,'child',link='rover_1/'+name+'_link')
            tag(uj,'origin',xyz=text_pose((x,y,WHEEL_Z)));tag(uj,'axis',xyz='0 1 0')
            joints.append(name+'_joint')
    for name,xyz in SENSORS.items():
        link=add_sdf_link(model,name,xyz,.1,(.05,.05,.05))
        j=tag(model,'joint',name=name+'_fixed',type='fixed');tag(j,'parent','base_link');tag(j,'child',name)
        tag(urdf,'link',name='rover_1/'+name)
        uj=tag(urdf,'joint',name=name+'_fixed',type='fixed')
        tag(uj,'parent',link='rover_1/base_link');tag(uj,'child',link='rover_1/'+name);tag(uj,'origin',xyz=text_pose(xyz))
        if name in ('camera_link','depth_link'):
            optical=name.replace('_link','_optical_frame');tag(urdf,'link',name='rover_1/'+optical)
            uj=tag(urdf,'joint',name=optical+'_fixed',type='fixed')
            tag(uj,'parent',link='rover_1/'+name);tag(uj,'child',link='rover_1/'+optical)
            tag(uj,'origin',rpy=f'{-math.pi/2} 0 {-math.pi/2}')
        if name=='imu_link':
            sensor=tag(link,'sensor',name='imu',type='imu');tag(sensor,'topic','/rover_1/imu')
            tag(sensor,'update_rate',50);tag(sensor,'always_on','true');tag(sensor,'gz_frame_id','rover_1/imu_link')
            imu=tag(sensor,'imu')
            for category,stddev in (('angular_velocity',.002),('linear_acceleration',.02)):
                group=tag(imu,category)
                for axis in ('x','y','z'):
                    noise=tag(tag(group,axis),'noise',type='gaussian')
                    tag(noise,'mean',0);tag(noise,'stddev',stddev)
            # Explicit orientation reference is gravity/world; EKF uses angular
            # velocity only in planar T3, never perfect simulated heading.
        elif name=='lidar_link':
            sensor=tag(link,'sensor',name='lidar',type='gpu_lidar');tag(sensor,'topic','/rover_1/scan')
            tag(sensor,'update_rate',10);tag(sensor,'always_on','true');tag(sensor,'gz_frame_id','rover_1/lidar_link')
            lidar=tag(sensor,'lidar');scan=tag(lidar,'scan');horizontal=tag(scan,'horizontal')
            for k,v in [('samples',360),('resolution',1),('min_angle',-math.pi),('max_angle',math.pi)]:tag(horizontal,k,v)
            ranges=tag(lidar,'range')
            for k,v in [('min',.2),('max',25),('resolution',.02)]:tag(ranges,k,v)
            noise=tag(lidar,'noise');tag(noise,'type','gaussian');tag(noise,'mean',0);tag(noise,'stddev',.01)
        else:
            depth=name=='depth_link'
            sensor=tag(link,'sensor',name='depth' if depth else 'camera',type='depth_camera' if depth else 'camera')
            tag(sensor,'topic','/rover_1/depth' if depth else '/rover_1/camera/image')
            tag(sensor,'update_rate',5);tag(sensor,'always_on','true')
            tag(sensor,'gz_frame_id','rover_1/'+name.replace('_link','_optical_frame'))
            camera=tag(sensor,'camera');tag(camera,'horizontal_fov',1.047)
            image=tag(camera,'image');tag(image,'width',320);tag(image,'height',240);tag(image,'format','R8G8B8')
            clip=tag(camera,'clip');tag(clip,'near',.1);tag(clip,'far',40)
    drive=tag(model,'plugin',filename='gz-sim-diff-drive-system',name='gz::sim::systems::DiffDrive')
    for joint in joints:tag(drive,'left_joint' if joint.split('_')[1].endswith('l') else 'right_joint',joint)
    for key,value in [('wheel_separation',TRACK),('wheel_radius',RADIUS),('topic','/rover_1/cmd_vel'),
                      ('odom_topic','/rover_1/odom_raw'),('tf_topic','/rover_1/gz_odom_tf_unused'),
                      ('frame_id','rover_1/odom'),('child_frame_id','rover_1/base_link'),
                      ('odom_publish_frequency',30),('min_velocity',-.4),('max_velocity',.4),
                      ('min_acceleration',-.3),('max_acceleration',.3)]:tag(drive,key,value)
    jsp=tag(model,'plugin',filename='gz-sim-joint-state-publisher-system',name='gz::sim::systems::JointStatePublisher')
    tag(jsp,'topic','/rover_1/joint_states')
    tag(jsp,'update_rate',50)
    for joint in joints:tag(jsp,'joint_name',joint)
    return sdf,urdf


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);args=p.parse_args()
    sdf,urdf=generate()
    for tree,path in ((sdf,args.out/'models/rover_1/model.sdf'),(urdf,args.out/'urdf/rover_1.urdf')):
        path.parent.mkdir(parents=True,exist_ok=True);ET.indent(tree);ET.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
    config=args.out/'models/rover_1/model.config'
    config.write_text('<model><name>REDLINE scenario rover</name><version>0.1</version><sdf version="1.9">model.sdf</sdf><description>Primitive SCENARIO integration rover; final art independent.</description></model>\n')
    (args.out/'geometry.json').write_text(json.dumps({'status':'SCENARIO','radius_m':RADIUS,'track_m':TRACK,
        'body_mass_kg':BODY_MASS,'body_size_m':BODY_SIZE,'wheel_center_z_m':WHEEL_Z,'root_ground_clearance_m':RADIUS-WHEEL_Z,
        'physics':'sixwheel skid steer; not Curiosity rocker bogie','tf_authority':'EKF odom->base; RSP joints; no Gazebo odom TF bridge'},indent=2)+'\n')

if __name__=='__main__':main()
