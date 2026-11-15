#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_load_runtime
export ROS_DOMAIN_ID=77 GZ_PARTITION=redline
"$REDLINE_SYSTEM_PYTHON" - <<'PY'
import json,math,time,subprocess
import rclpy
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry,Path
from sensor_msgs.msg import LaserScan
rclpy.init();node=rclpy.create_node('t3_readonly_diagnostics');values={};counts={};subs=[]
def observe(topic,msg):
    counts[topic]=counts.get(topic,0)+1
    if isinstance(msg,Twist):values[topic]={'vx':msg.linear.x,'wz':msg.angular.z}
    elif isinstance(msg,Odometry):values[topic]={'x':msg.pose.pose.position.x,'y':msg.pose.pose.position.y,'z':msg.pose.pose.position.z,'vx':msg.twist.twist.linear.x,'wz':msg.twist.twist.angular.z,'frame':msg.header.frame_id,'child':msg.child_frame_id}
    elif isinstance(msg,Path):values[topic]={'frame':msg.header.frame_id,'poses':len(msg.poses),'xy':[[p.pose.position.x,p.pose.position.y] for p in msg.poses[:100]],'max_segment_m':max((math.hypot(a.pose.position.x-b.pose.position.x,a.pose.position.y-b.pose.position.y) for a,b in zip(msg.poses,msg.poses[1:])),default=0)}
    else:
        finite=[r for r in msg.ranges if math.isfinite(r)]
        values[topic]={'frame':msg.header.frame_id,'finite':len(finite),'min':min(finite) if finite else None,'max':max(finite) if finite else None,'rays':len(msg.ranges)}
for topic,kind in [(f'/rover_1/{t}',Twist) for t in ('cmd_vel_nav','cmd_vel_gated','cmd_vel','cmd_vel_sim')]+[('/rover_1/odom',Odometry),('/rover_1/odom_raw',Odometry),('/rover_1/scan',LaserScan),('/rover_1/plan',Path)]:
    subs.append(node.create_subscription(kind,topic,lambda msg,t=topic:observe(t,msg),qos_profile_sensor_data))
deadline=time.monotonic()+4
while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.1)
try:
    sample=subprocess.run(['gz','topic','-e','-t','/world/bxw/dynamic_pose/info','-n','1','--json-output'],capture_output=True,text=True,timeout=5,check=True)
    pose=next(p for p in json.loads(sample.stdout).get('pose',[]) if p.get('name')=='rover_1')
except Exception as error:pose=str(error)
print(json.dumps({'counts':counts,'latest':values,'measured_rover':pose},indent=2))
node.destroy_node();rclpy.try_shutdown()
PY
