#!/usr/bin/env python3
"""Bounded live Nav2/sensor check; goal and actual travel are recorded separately.

This is simulation-only. Planner uses wheel/IMU EKF; this checker may use Gazebo
ground truth for independent measurement, never as localization input.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import qos_profile_action_status_default, qos_profile_sensor_data
from action_msgs.msg import GoalStatusArray
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from lifecycle_msgs.srv import GetState
from sensor_msgs.msg import Image, Imu, LaserScan
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener


GOAL_TOPIC='/rover_1/goal_pose'
GOAL_EVIDENCE_TOPIC='/redline/t3/rviz_goal_evidence'
STATUS_TOPIC='/rover_1/navigate_to_pose/_action/status'


def stamp_ns(stamp):
    return int(stamp.sec)*1_000_000_000+int(stamp.nanosec)


def decode_observed_goal(value):
    """Decode the C++ observer's original pose and matched real DDS writer."""
    if value['schema']!='redline.t3.rviz-goal.v1' or value['goal_topic']!=GOAL_TOPIC:
        raise ValueError('Unexpected RViz observer evidence schema/topic')
    publisher=value['publisher'];gid=bytes.fromhex(publisher['publisher_gid'])
    if not gid or not any(gid):raise ValueError('Missing RViz DDS writer GID')
    data=value['pose'];message=PoseStamped()
    message.header.stamp.sec=data['stamp_sec'];message.header.stamp.nanosec=data['stamp_nanosec']
    message.header.frame_id=data['frame_id']
    message.pose.position.x,message.pose.position.y,message.pose.position.z=data['position']
    (message.pose.orientation.x,message.pose.orientation.y,
     message.pose.orientation.z,message.pose.orientation.w)=data['orientation']
    return message,publisher


class RvizGoalTracker:
    """Correlate one fresh RViz pose with one newly accepted Nav2 UUID.

    Status messages may arrive before the pose callback, since these are separate
    topics. Accepted-goal timestamps and the UUID baseline remove old retained
    actions; multiple fresh actions or a second distinct pose fail closed.
    """
    def __init__(self,expected):
        self.expected=expected;self.actions={};self.baseline=set();self.armed_ns=None
        self.goal=None;self.goal_stamp_ns=None;self.goal_signature=None
        self.goal_uuid=None;self.status=None;self.error=None;self.ignored=Counter()
        self.publisher=None;self.goal_received_at_utc=None
        self.observer_source_timestamp_ns=None

    def arm(self,now_ns):
        if self.armed_ns is not None:raise RuntimeError('RViz goal tracker already armed')
        self.baseline=set(self.actions);self.armed_ns=int(now_ns)

    def receive_goal(self,msg,publisher):
        if self.armed_ns is None:
            self.ignored['before_readiness']+=1;return
        if publisher is None or publisher.get('node_name') not in ('rviz_navigation','rviz2'):
            self.ignored['non_rviz_or_unresolved_publisher']+=1;return
        sent=stamp_ns(msg.header.stamp)
        if sent<=0 or sent<self.armed_ns:
            self.ignored['old_or_unstamped_pose']+=1;return
        p,q=msg.pose.position,msg.pose.orientation
        signature=(sent,msg.header.frame_id,p.x,p.y,p.z,q.x,q.y,q.z,q.w)
        if self.goal is not None:
            if signature==self.goal_signature:self.ignored['duplicate_pose']+=1
            else:self.error='A second distinct RViz goal arrived during this acceptance run'
            return
        if msg.header.frame_id!='map':
            self.error='RViz goal must be expressed in map';return
        if not all(math.isfinite(v) for v in (p.x,p.y,p.z,q.x,q.y,q.z,q.w)):
            self.error='RViz goal contains non-finite pose values';return
        norm=math.sqrt(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w)
        if abs(norm-1)>0.01:
            self.error='RViz goal quaternion is not normalized';return
        if math.hypot(p.x-self.expected['map_x_m'],p.y-self.expected['map_y_m'])>1.0:
            self.error='RViz goal is outside the controlled manifest target (1 m tolerance)';return
        self.goal={'map_x_m':float(p.x),'map_y_m':float(p.y),
                   'ground_z_m':self.expected['ground_z_m'],
                   'yaw_rad':math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))}
        self.goal_signature=signature;self.goal_stamp_ns=sent;self.publisher=publisher
        self.goal_received_at_utc=datetime.now(timezone.utc).isoformat()
        self._correlate()

    def receive_status(self,msg):
        for entry in msg.status_list:
            uuid=bytes(entry.goal_info.goal_id.uuid).hex()
            if len(uuid)!=32 or uuid=='0'*32:continue
            accepted=stamp_ns(entry.goal_info.stamp)
            self.actions[uuid]={'accepted_stamp_ns':accepted,'status':int(entry.status)}
        self._correlate()

    def _correlate(self):
        if self.goal is None or self.error:return
        eligible=[uuid for uuid,value in self.actions.items()
                  if uuid not in self.baseline and value['accepted_stamp_ns']>=self.goal_stamp_ns
                  and value['accepted_stamp_ns']>=self.armed_ns and value['status'] in (1,2,3,4,5,6)]
        if len(eligible)>1:
            self.error='Multiple new Nav2 action UUIDs prevent unambiguous RViz goal correlation';return
        if not eligible:return
        uuid=eligible[0]
        if self.goal_uuid is not None and self.goal_uuid!=uuid:
            self.error='Nav2 changed goal UUID during the RViz acceptance run';return
        self.goal_uuid=uuid;self.status=self.actions[uuid]['status']
        if self.status in (5,6):
            self.error=f'RViz Nav2 goal ended with status {self.status} (canceled/aborted)'

    def evidence(self):
        return {'goal_topic':GOAL_TOPIC,'status_topic':STATUS_TOPIC,
                'baseline_uuids':sorted(self.baseline),'armed_sim_stamp_ns':self.armed_ns,
                'goal_pose_stamp_ns':self.goal_stamp_ns,'goal_uuid':self.goal_uuid,
                'action_status':self.status,'publisher':self.publisher,
                'goal_received_at_utc':self.goal_received_at_utc,
                'evidence_topic':GOAL_EVIDENCE_TOPIC,
                'observer_source_timestamp_ns':self.observer_source_timestamp_ns,
                'ignored_messages':dict(self.ignored),'error':self.error}


def measured_pose():
    """Evaluation-only Gazebo model pose; never published into localization."""
    value=subprocess.run(['gz','topic','-e','-t','/world/bxw/dynamic_pose/info','-n','1','--json-output'],
        capture_output=True,text=True,timeout=10,check=True)
    poses=json.loads(value.stdout).get('pose',[])
    model=next((p for p in poses if p.get('name')=='rover_1'),None)
    if model is None:raise RuntimeError('Evaluation pose lacks rover_1 model')
    position=model['position']
    return [float(position.get(k,0)) for k in ('x','y','z')]


class Checker(Node):
    def __init__(self,rviz_target=None):
        super().__init__('t3_navigation_verifier',parameter_overrides=[rclpy.parameter.Parameter('use_sim_time',value=True)])
        self.counts=Counter();self.samples={};self.odom=None;self.positions=[]
        self.subs=[]
        for topic,kind in [('/rover_1/scan',LaserScan),('/rover_1/imu',Imu),('/rover_1/camera/image',Image),('/rover_1/depth/image',Image),('/rover_1/odom',Odometry)]:
            self.subs.append(self.create_subscription(kind,topic,lambda msg,t=topic:self.received(t,msg),qos_profile_sensor_data))
        self.buffer=Buffer();self.listener=TransformListener(self.buffer,self)
        self.client=ActionClient(self,NavigateToPose,'/rover_1/navigate_to_pose')
        self.rviz=RvizGoalTracker(rviz_target) if rviz_target is not None else None
        if self.rviz is not None:
            self.subs.append(self.create_subscription(GoalStatusArray,STATUS_TOPIC,
                self.rviz.receive_status,qos_profile_action_status_default))
            self.subs.append(self.create_subscription(String,GOAL_EVIDENCE_TOPIC,self.rviz_goal,10))

    def rviz_goal(self,message):
        try:
            endpoints=self.get_publishers_info_by_topic(GOAL_EVIDENCE_TOPIC)
            if len(endpoints)!=1 or endpoints[0].node_name!='rviz_goal_observer':
                raise ValueError('RViz evidence must have one managed observer publisher')
            value=json.loads(message.data);pose,publisher=decode_observed_goal(value)
            self.rviz.receive_goal(pose,publisher)
            if self.rviz.goal is not None:self.rviz.observer_source_timestamp_ns=value['source_timestamp_ns']
        except (KeyError,TypeError,ValueError,AssertionError) as error:
            self.rviz.error=f'Invalid RViz observer evidence: {error}'

    def received(self,topic,msg):
        self.counts[topic]+=1
        if topic.endswith('/odom'):
            self.odom=msg
            if len(self.positions)<10000:self.positions.append([msg.pose.pose.position.x,msg.pose.pose.position.y])
        elif isinstance(msg,Image):self.samples[topic]={'width':msg.width,'height':msg.height,'encoding':msg.encoding,'frame_id':msg.header.frame_id,'data_bytes':len(msg.data)}
        elif isinstance(msg,LaserScan):
            valid=[x for x in msg.ranges if math.isfinite(x) and msg.range_min<=x<=msg.range_max]
            self.samples[topic]={'rays':len(msg.ranges),'finite_returns':len(valid),'frame_id':msg.header.frame_id}
        else:self.samples[topic]={'frame_id':msg.header.frame_id}

    def wait(self,predicate,seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if predicate():return True
            rclpy.spin_once(self,timeout_sec=.1)
            if predicate():return True
        return False

    def wait_active(self,seconds=45):
        state=self.create_client(GetState,'/rover_1/bt_navigator/get_state')
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if not state.wait_for_service(timeout_sec=1):continue
            request=state.call_async(GetState.Request())
            if self.wait(request.done,2) and request.result().current_state.id==3:return True
        return False


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--terrain',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);p.add_argument('--timeout',type=float,default=180)
    p.add_argument('--root-clearance',type=float,default=.5)
    p.add_argument('--rviz-goal',action='store_true',help='Wait for the real RViz goal topic; never send a goal')
    p.add_argument('--goal-wait-timeout',type=float,default=90,
                   help='Bounded operator/UI preparation time; does not change navigation deadline')
    args=p.parse_args();terrain=json.loads(args.terrain.read_text())
    if not math.isfinite(args.goal_wait_timeout) or not 1<=args.goal_wait_timeout<=600:
        p.error('goal-wait-timeout must be in [1,600] seconds')
    rclpy.init();node=Checker(terrain['goal'] if args.rviz_goal else None)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'passed':False,
            'mode':'observed RViz goal_pose + new Nav2 action UUID' if args.rviz_goal else 'programmatic NavigateToPose; not an observed RViz click'}
    try:
        if not node.wait(lambda:len(node.counts)==5 and min(node.counts.values())>=2,45):raise RuntimeError('Missing live sensors/filtered odometry')
        if not node.wait_active():raise RuntimeError('Nav2 navigator did not reach active state')
        if not node.client.wait_for_server(timeout_sec=30):raise RuntimeError('Nav2 action unavailable')
        start=node.buffer.lookup_transform('map','rover_1/base_link',rclpy.time.Time())
        report['start_map_xy']=[start.transform.translation.x,start.transform.translation.y]
        report['measured_start_map_xyz']=measured_pose()
        if args.rviz_goal:
            # measured_pose blocks without spinning this node. Drain old goal
            # callbacks while still unarmed and refresh /clock before taking
            # the UUID/time baseline; otherwise a queued pre-readiness click
            # could look newer than this node's stale simulation clock.
            node.wait(lambda:False,.25)
            node.rviz.arm(node.get_clock().now().nanoseconds)
            report['rviz_goal_wait_timeout_s']=args.goal_wait_timeout
            print(json.dumps({'event':'rviz_goal_ready','goal_topic':GOAL_TOPIC,
                  'expected_target':terrain['goal'],'target_tolerance_m':1.0,
                  'start_map_xy':report['start_map_xy'],
                  'measured_start_map_xyz':report['measured_start_map_xyz'],
                  'goal_wait_timeout_s':args.goal_wait_timeout}),flush=True)
            if not node.wait(lambda:node.rviz.goal is not None or node.rviz.error is not None,args.goal_wait_timeout):
                raise RuntimeError(f'No fresh RViz goal received within {args.goal_wait_timeout:g} seconds')
            if node.rviz.error:raise RuntimeError(node.rviz.error)
            target=node.rviz.goal
            report['goal_map']=target
            # The navigation deadline begins when the pose callback receives
            # the goal. The topic consumer, bt_navigator, owns action submission.
            if not node.wait(lambda:node.rviz.error is not None or node.rviz.status in (4,5,6),args.timeout):
                raise RuntimeError('RViz navigation timed out waiting for a new UUID terminal status')
            if node.rviz.error:raise RuntimeError(node.rviz.error)
            status=node.rviz.status;report['action_status']=status
            report['goal_accepted']=node.rviz.goal_uuid is not None
        else:
            target=terrain['goal'];goal=NavigateToPose.Goal();pose=PoseStamped()
            pose.header.frame_id='map';pose.header.stamp=node.get_clock().now().to_msg()
            pose.pose.position.x=target['map_x_m'];pose.pose.position.y=target['map_y_m']
            pose.pose.orientation.z=math.sin(target['yaw_rad']/2);pose.pose.orientation.w=math.cos(target['yaw_rad']/2);goal.pose=pose
            request=node.client.send_goal_async(goal)
            if not node.wait(request.done,15):raise RuntimeError('Goal request timeout')
            handle=request.result();report['goal_accepted']=handle.accepted
            if not handle.accepted:raise RuntimeError('Nav2 rejected goal')
            result=handle.get_result_async()
            if not node.wait(result.done,args.timeout):
                handle.cancel_goal_async();raise RuntimeError('Navigation timed out')
            status=result.result().status;report['action_status']=status
        final=node.buffer.lookup_transform('map','rover_1/base_link',rclpy.time.Time())
        xy=[final.transform.translation.x,final.transform.translation.y]
        error=math.hypot(xy[0]-target['map_x_m'],xy[1]-target['map_y_m'])
        travel=math.hypot(xy[0]-report['start_map_xy'][0],xy[1]-report['start_map_xy'][1])
        report.update(final_map_xy=xy,goal_map=target,goal_error_m=error,estimated_displacement_m=travel,
                      passed=status==4 and error<=.7 and travel>=3)
        physical=measured_pose();report['measured_final_map_xyz']=physical
        physical_error=math.hypot(physical[0]-target['map_x_m'],physical[1]-target['map_y_m'])
        physical_travel=math.hypot(physical[0]-report['measured_start_map_xyz'][0],physical[1]-report['measured_start_map_xyz'][1])
        report['measured_goal_error_m']=physical_error;report['measured_displacement_m']=physical_travel
        zerror=abs(physical[2]-(target['ground_z_m']+args.root_clearance));report['measured_ground_contact_height_error_m']=zerror
        report['expected_root_clearance_m']=args.root_clearance
        report['passed']=report['passed'] and physical_error<=1.0 and physical_travel>=3 and zerror<=.5
        if not report['passed']:raise RuntimeError('Nav2 result/position/displacement gate failed')
    except Exception as error:
        report['passed']=False;report['error']=str(error)
    finally:
        if node.rviz is not None:
            report['rviz_goal']=node.rviz.evidence()
            if node.rviz.status is not None:report['action_status']=node.rviz.status
            if node.rviz.goal is not None:report['goal_map']=node.rviz.goal
            report['goal_accepted']=node.rviz.goal_uuid is not None
        report['topic_counts']=dict(node.counts);report['sensor_samples']=node.samples
        report['estimated_trajectory_xy']=node.positions
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2)+'\n')
        node.destroy_node();rclpy.try_shutdown()
    print(json.dumps({k:v for k,v in report.items() if k!='estimated_trajectory_xy'},indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
