#!/usr/bin/env python3
"""Bounded simulation-only turn commissioning; navigation must be absent."""
import argparse
from datetime import datetime,timezone
import json
import hashlib
import math
from pathlib import Path
import subprocess
import time
import rclpy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu,JointState
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data


def pose():
    result=subprocess.run(['gz','topic','-e','-t','/world/bxw/dynamic_pose/info','-n','1','--json-output'],
                          capture_output=True,text=True,check=True,timeout=10)
    return next(p for p in json.loads(result.stdout)['pose'] if p.get('name')=='rover_1')


def yaw(model):
    q=model['orientation'];x,y,z,w=(float(q.get(k,0)) for k in ('x','y','z','w'))
    return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();rclpy.init();node=rclpy.create_node('t3_rotation_probe')
    samples=[];sub=node.create_subscription(Imu,'/rover_1/imu',lambda m:samples.append(float(m.angular_velocity.z)),qos_profile_sensor_data)
    joints=[];odometry=[]
    joint_sub=node.create_subscription(JointState,'/rover_1/joint_states',lambda m:joints.append(dict(zip(m.name,m.position))),qos_profile_sensor_data)
    odom_sub=node.create_subscription(Odometry,'/rover_1/odom_raw',lambda m:odometry.append([m.twist.twist.linear.x,m.twist.twist.angular.z]),qos_profile_sensor_data)
    pub=node.create_publisher(Twist,'/rover_1/cmd_vel',10)
    report={'created_at_utc':datetime.now(timezone.utc).isoformat(),'passed':False,'simulation_only':True,
            'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        end=time.monotonic()+45
        # The world spawns 10 cm above contact. Wait two physics seconds of
        # 50 Hz IMU data, rather than commanding the rover during the drop.
        while len(samples)<100 and time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.05)
        if len(samples)<100:raise RuntimeError('No settled sensor window')
        report['readiness_imu_samples']=len(samples)
        # Reject a competing controller. This probe is the sole cmd_vel owner.
        publishers=node.get_publishers_info_by_topic('/rover_1/cmd_vel')
        if len(publishers)!=1 or publishers[0].node_name!=node.get_name():raise RuntimeError('Competing command publisher')
        before=pose();first_joints=joints[-1] if joints else {};command=Twist();command.angular.z=.2
        end=time.monotonic()+8
        while time.monotonic()<end:
            pub.publish(command);rclpy.spin_once(node,timeout_sec=.05)
        end=time.monotonic()+1
        while time.monotonic()<end:
            pub.publish(Twist());rclpy.spin_once(node,timeout_sec=.05)
        after=pose();delta=math.atan2(math.sin(yaw(after)-yaw(before)),math.cos(yaw(after)-yaw(before)))
        p0,p1=before['position'],after['position']
        distance=math.hypot(float(p1.get('x',0))-float(p0.get('x',0)),float(p1.get('y',0))-float(p0.get('y',0)))
        report.update(yaw_before_rad=yaw(before),yaw_after_rad=yaw(after),physical_yaw_change_rad=delta,
                      physical_translation_m=distance,imu_max_abs_wz_radps=max(map(abs,samples)),
                      joint_delta_rad={name:value-first_joints.get(name,value) for name,value in (joints[-1] if joints else {}).items()},
                      maximum_encoder_vx_mps=max((abs(v[0]) for v in odometry),default=None),
                      maximum_encoder_wz_radps=max((abs(v[1]) for v in odometry),default=None),
                      command_wz_radps=.2,command_duration_s=8,passed=.5<=delta<=2.2 and distance<=.5)
    except Exception as error:report['error']=str(error)
    finally:
        pub.publish(Twist());node.destroy_node();rclpy.try_shutdown()
        args.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
