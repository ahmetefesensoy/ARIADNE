#!/usr/bin/env bash
# Read-only commissioning evidence. No goals, velocity or synthetic sensor data.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_load_runtime
export ROS_DOMAIN_ID=77 GZ_PARTITION=redline
exec "$REDLINE_SYSTEM_PYTHON" - "$@" <<'PY'
from collections import Counter
from datetime import datetime,timezone
import argparse,json,math,time
import rclpy
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy
from nav_msgs.msg import OccupancyGrid,Path
from map_msgs.msg import OccupancyGridUpdate
from sensor_msgs.msg import LaserScan,JointState,PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import String
import numpy as np
from geometry_msgs.msg import Twist
parser=argparse.ArgumentParser();parser.add_argument('--duration',type=float,default=8)
args=parser.parse_args()
if not 1<=args.duration<=60:parser.error('duration must be in [1,60] seconds')
rclpy.init();node=rclpy.create_node('redline_perception_inspector')
counts=Counter();samples={};subs=[];peaks={}
def observe(topic,msg):
    counts[topic]+=1
    if isinstance(msg,LaserScan):
        values=[v for v in msg.ranges if math.isfinite(v) and msg.range_min<=v<=msg.range_max]
        samples[topic]={'frame':msg.header.frame_id,'rays':len(msg.ranges),
                        'valid_returns':len(values),'nearest_m':min(values) if values else None}
        previous=peaks.setdefault(topic,{'max_valid_returns':0,'nearest_ever_m':None})
        previous['max_valid_returns']=max(previous['max_valid_returns'],len(values))
        if values:previous['nearest_ever_m']=min(min(values),previous['nearest_ever_m'] or float('inf'))
    elif isinstance(msg,(OccupancyGrid,OccupancyGridUpdate)):
        samples[topic]={'frame':msg.header.frame_id,
            'occupied_cells':sum(v>=99 for v in msg.data),'unknown_cells':sum(v<0 for v in msg.data),
            'inflated_cells':sum(0<v<99 for v in msg.data)}
        if isinstance(msg,OccupancyGrid):samples[topic].update(resolution_m=msg.info.resolution,width=msg.info.width,height=msg.info.height)
        else:samples[topic].update(width=msg.width,height=msg.height,x=msg.x,y=msg.y)
        previous=peaks.setdefault(topic,{'max_occupied_cells':0,'max_inflated_cells':0})
        for key in ('occupied_cells','inflated_cells'):previous['max_'+key]=max(previous['max_'+key],samples[topic][key])
    elif isinstance(msg,Path):
        samples[topic]={'frame':msg.header.frame_id,'poses':len(msg.poses),
            'start_xy':[[p.pose.position.x,p.pose.position.y] for p in msg.poses[:1]],
            'end_xy':[[p.pose.position.x,p.pose.position.y] for p in msg.poses[-1:]]}
        if len(msg.poses)>1:
            first,last=msg.poses[0].pose.position,msg.poses[-1].pose.position
            dx,dy=last.x-first.x,last.y-first.y;length=math.hypot(dx,dy)
            signed=[(dx*(p.pose.position.y-first.y)-dy*(p.pose.position.x-first.x))/length for p in msg.poses] if length else [0]
            deviation=max(map(abs,signed))
            previous=peaks.setdefault(topic,{'max_lateral_deviation_m':0})
            previous['max_lateral_deviation_m']=max(previous['max_lateral_deviation_m'],deviation)
            history=previous.setdefault('signed_path_history',[])
            if len(history)<200:history.append({'sim_stamp_s':msg.header.stamp.sec+msg.header.stamp.nanosec/1e9,
                                                'minimum_m':min(signed),'maximum_m':max(signed)})
    elif isinstance(msg,PointCloud2):
        values=point_cloud2.read_points_numpy(msg,field_names=['x','y','z'],skip_nans=False).reshape(-1,3)
        count=int(np.isfinite(values).all(axis=1).sum())
        samples[topic]={'frame':msg.header.frame_id,'dimensions':[msg.width,msg.height],'finite_points':count}
        previous=peaks.setdefault(topic,{'max_finite_points':0});previous['max_finite_points']=max(previous['max_finite_points'],count)
    elif isinstance(msg,String):
        value=json.loads(msg.data);samples[topic]=value
        previous=peaks.setdefault(topic,{'valid_count':0,'invalid_count':0,'maximum_processing_ms':0})
        previous['valid_count' if value['valid'] else 'invalid_count']+=1
        previous['maximum_processing_ms']=max(previous['maximum_processing_ms'],value['processing_wall_ms'])
    elif isinstance(msg,Twist):
        samples[topic]={'vx_mps':msg.linear.x,'wz_radps':msg.angular.z}
        previous=peaks.setdefault(topic,{'max_abs_vx_mps':0,'max_abs_wz_radps':0})
        previous['max_abs_vx_mps']=max(previous['max_abs_vx_mps'],abs(msg.linear.x))
        previous['max_abs_wz_radps']=max(previous['max_abs_wz_radps'],abs(msg.angular.z))
    else:samples[topic]={'joint_names':list(msg.name),'positions_rad':list(msg.position)}
latched=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
streams=[('/rover_1/scan',LaserScan,qos_profile_sensor_data),
         ('/rover_1/joint_states',JointState,qos_profile_sensor_data),
         ('/rover_1/lidar_3d/points',PointCloud2,qos_profile_sensor_data),
         ('/rover_1/lidar/ground',PointCloud2,qos_profile_sensor_data),
         ('/rover_1/lidar/obstacles',PointCloud2,qos_profile_sensor_data),
         ('/rover_1/lidar/segmentation_status',String,10),
         ('/rover_1/global_costmap/costmap',OccupancyGrid,latched),
         ('/rover_1/local_costmap/costmap',OccupancyGrid,latched),
         ('/rover_1/global_costmap/costmap_updates',OccupancyGridUpdate,latched),
         ('/rover_1/local_costmap/costmap_updates',OccupancyGridUpdate,latched),
         ('/rover_1/unsmoothed_plan',Path,10),
         ('/rover_1/cmd_vel_nav',Twist,qos_profile_sensor_data),
         ('/rover_1/cmd_vel_gated',Twist,qos_profile_sensor_data),
         ('/rover_1/cmd_vel',Twist,qos_profile_sensor_data),
         ('/rover_1/cmd_vel_sim',Twist,qos_profile_sensor_data),
         ('/rover_1/plan',Path,10)]
for topic,kind,qos in streams:
    subs.append(node.create_subscription(kind,topic,lambda msg,t=topic:observe(t,msg),qos))
deadline=time.monotonic()+args.duration
probe_error=None
try:
    while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.1)
except KeyboardInterrupt:pass
except RuntimeError as error:probe_error=str(error)
print(json.dumps({'observed_at_utc':datetime.now(timezone.utc).isoformat(),
    'read_only':True,'counts':dict(counts),'samples':samples,'peaks':peaks,'probe_error':probe_error,
    'missing':[topic for topic,_,_ in streams if not counts[topic]],
    'limits':['Live streams are not proof of obstacle avoidance or calibrated robot dynamics.']},indent=2))
node.destroy_node();rclpy.try_shutdown()
PY
