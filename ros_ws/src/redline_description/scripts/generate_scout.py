#!/usr/bin/env python3
"""Original SCENARIO four-rotor scout, independent of the presentation mesh.

Gazebo Harmonic plugin parameters are based on the installed Open Robotics
multicopter_velocity_control.sdf API example (Apache-2.0); no example robot
geometry is copied. Density, mass, gains and rotor capacity are scenario
assumptions, not Ingenuity or validated Mars flight hardware.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def model_sdf(x=0.,y=0.,z=1.,name='scout_1',density=.018):
    coefficient=8.54858e-6*density/1.225
    body='''<link name="base_link"><inertial><mass>1</mass><inertia><ixx>.022</ixx><iyy>.022</iyy><izz>.042</izz></inertia></inertial><collision name="body_collision"><geometry><box><size>.5 .5 .12</size></box></geometry></collision><visual name="body_visual"><geometry><box><size>.5 .5 .12</size></box></geometry><material><ambient>.75 .7 .6 1</ambient><diffuse>.75 .7 .6 1</diffuse></material></visual></link>'''
    parts=[];motors=[];configuration=[]
    for i,(rx,ry,direction) in enumerate(((.35,.35,1),(-.35,-.35,1),(.35,-.35,-1),(-.35,.35,-1))):
        parts.append(f'''<link name="rotor_{i}"><pose>{rx} {ry} .08 0 0 0</pose><inertial><mass>.01</mass><inertia><ixx>.00001</ixx><iyy>.00001</iyy><izz>.00002</izz></inertia></inertial><visual name="rotor_visual"><geometry><cylinder><radius>.15</radius><length>.01</length></cylinder></geometry></visual></link><joint name="rotor_{i}_joint" type="revolute"><parent>base_link</parent><child>rotor_{i}</child><axis><xyz>0 0 1</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis></joint>''')
        motors.append(f'''<plugin filename="gz-sim-multicopter-motor-model-system" name="gz::sim::systems::MulticopterMotorModel"><robotNamespace>{name}</robotNamespace><jointName>rotor_{i}_joint</jointName><linkName>rotor_{i}</linkName><turningDirection>{'ccw' if direction==1 else 'cw'}</turningDirection><timeConstantUp>.0125</timeConstantUp><timeConstantDown>.025</timeConstantDown><maxRotVelocity>10000</maxRotVelocity><motorConstant>{coefficient}</motorConstant><momentConstant>.016</momentConstant><commandSubTopic>command/motor_speed</commandSubTopic><actuator_number>{i}</actuator_number><rotorDragCoefficient>1.2e-6</rotorDragCoefficient><rollingMomentCoefficient>1e-8</rollingMomentCoefficient><motorSpeedPubTopic>motor_speed/{i}</motorSpeedPubTopic><rotorVelocitySlowdownSim>10</rotorVelocitySlowdownSim><motorType>velocity</motorType></plugin>''')
        configuration.append(f'<rotor><jointName>rotor_{i}_joint</jointName><forceConstant>{coefficient}</forceConstant><momentConstant>.016</momentConstant><direction>{direction}</direction></rotor>')
    controller=f'''<plugin filename="gz-sim-multicopter-control-system" name="gz::sim::systems::MulticopterVelocityControl"><robotNamespace>{name}</robotNamespace><commandSubTopic>command/twist</commandSubTopic><enableSubTopic>enable</enableSubTopic><comLinkName>base_link</comLinkName><velocityGain>2.7 2.7 2.7</velocityGain><attitudeGain>2 2 .15</attitudeGain><angularRateGain>.4 .4 .18</angularRateGain><maximumLinearAcceleration>.5 .5 .8</maximumLinearAcceleration><maximumLinearVelocity>5 5 3</maximumLinearVelocity><maximumAngularVelocity>.6 .6 .35</maximumAngularVelocity><rotorConfiguration>{''.join(configuration)}</rotorConfiguration></plugin>'''
    odom=f'''<plugin filename="gz-sim-odometry-publisher-system" name="gz::sim::systems::OdometryPublisher"><dimensions>3</dimensions><odom_publish_frequency>50</odom_publish_frequency><odom_topic>/{name}/physics/odometry</odom_topic></plugin>'''
    return f'<?xml version="1.0"?><sdf version="1.9"><model name="{name}"><pose>{x} {y} {z} 0 0 0</pose>{body}{"".join(parts)}{"".join(motors)}{controller}{odom}</model></sdf>'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--xyz',type=float,nargs=3,default=(0,0,1))
    parser.add_argument('--density',type=float,default=.018)
    args=parser.parse_args()
    if not all(math.isfinite(v) for v in args.xyz) or not math.isfinite(args.density) or args.density<=0:
        raise ValueError('finite spawn and positive density required')
    args.out.mkdir(parents=True,exist_ok=True)
    path=args.out/'scout_1.sdf';path.write_text(model_sdf(*args.xyz,density=args.density))
    record={'status':'SCENARIO','mass_kg':1.04,'density_kg_m3':args.density,'gravity_m_s2':3.721,
            'pose_origin_map_m':args.xyz,'physics_authority':'Gazebo; no pose setters after spawn',
            'art':'original primitive collision and visual; user scout mesh remains a separate presentation asset',
            'plugin_api_reference':'Open Robotics Gazebo Harmonic 8.15 multicopter_velocity_control.sdf (Apache-2.0)',
            'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (args.out/'scout_1.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
