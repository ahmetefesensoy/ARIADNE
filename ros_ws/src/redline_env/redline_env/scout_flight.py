"""ExecuteScout through physical Gazebo motor/velocity control, never pose setters.

The velocity plugin uses Gazebo state feedback; this is not a tested flight
estimator. ROS owns the action and commands; Gazebo owns physics. Optional
truth_file enables an explicitly SIMULATED observation adapter at visited
waypoints, not camera/LiDAR measurements. Empty adapter means PARTIAL result
with no scientific evidence, even after successful physical flight.
"""
from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import TransformStamped,PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

from redline_core.planning import load_planning_grid
from redline_core.truth import load_truth, survey_evidence
from redline_core.scout_control import flight_velocity_setpoint, world_to_body_velocity
from redline_msgs.action import ExecuteScout
from redline_msgs.msg import CrewState, EvidenceRecord, MissionState, Provenance

STATE_QOS=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)
MAP_QOS=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
EVENT_QOS=QoSProfile(depth=100,reliability=ReliabilityPolicy.RELIABLE)


@dataclass(frozen=True)
class PhysicsPose:
    stamp_s: float
    xyz: tuple[float,float,float]
    quat: tuple[float,float,float,float]
    velocity: tuple[float,float,float]
    received: float


class ScoutFlightNode(Node):
    def __init__(self, *, transport_factory=None, **kwargs):
        super().__init__('scout_flight',**kwargs)
        self.vehicle=str(self.declare_parameter('vehicle_id','scout_1').value)
        self.origin=tuple(self.declare_parameter('origin_map_xyz',[0.,0.,0.]).value)
        self.crew_ids=list(self.declare_parameter('crew_ids',['EV1']).value)
        self.speed=float(self.declare_parameter('speed_m_s',3.).value)
        self.power=float(self.declare_parameter('power_w',300.).value)
        self.battery=float(self.declare_parameter('battery_wh',100.).value)
        self.spacing=float(self.declare_parameter('survey_spacing_m',12.).value)
        self.max_age=float(self.declare_parameter('max_state_age_s',3.).value)
        self.max_distance=float(self.declare_parameter('max_distance_from_home_m',200.).value)
        self.separation=float(self.declare_parameter('crew_separation_m',30.).value)
        self.max_flight=float(self.declare_parameter('max_flight_s',600.).value)
        self.command_accel=float(self.declare_parameter('command_accel_m_s2',.45).value)
        self.vertical_accel=float(self.declare_parameter('vertical_accel_m_s2',.65).value)
        self.ground=float(self.declare_parameter('home_ground_z_m',0.).value)
        grid_path=str(self.declare_parameter('planning_grid','').value)
        truth_path=str(self.declare_parameter('truth_file','').value)
        if (len(self.origin)!=3 or not all(math.isfinite(v) for v in self.origin) or not self.crew_ids or
                not all(math.isfinite(v) and v>0 for v in (self.speed,self.power,self.battery,self.spacing,self.max_age,self.max_distance,self.separation,self.max_flight)) or
                not math.isfinite(self.ground) or self.speed>5 or self.separation<30 or self.max_flight>900 or
                not math.isfinite(self.command_accel) or not 0<self.command_accel<=1 or not math.isfinite(self.vertical_accel) or not 0<self.vertical_accel<=1.5):
            raise ValueError('finite bounded SCENARIO flight parameters and >=30 m crew separation required')
        self.grid=load_planning_grid(grid_path)[0] if grid_path else None
        if truth_path and not self.grid:raise ValueError('SIMULATED observer requires the planning grid')
        self.truth=load_truth(truth_path) if truth_path else None
        self._lock=threading.RLock();self._pose=None;self._crew={};self._phase=None;self._phase_receipt=-math.inf
        self._busy=False;self._seen=set();self._last_published=-1.;self._evidence_ids=[];self._evidence_keys=set()
        self._flight_stage='PARKED';self._flight_progress=0.;self._request_id='';self._flight_start=None;self._progress_base=0.;self._progress_span=0.
        self._setpoint=(0.,0.,0.);self._setpoint_stamp=None
        for crew in self.crew_ids:
            self.create_subscription(PoseStamped,f'/crew/{crew}/pose',lambda m,c=crew:self._on_crew(c,m),STATE_QOS)
        self.create_subscription(MissionState,'/redline/mission/state',self._on_phase,MAP_QOS)
        # Production uses the installed Gazebo Transport binding. Injection is
        # only a constructor dependency for tests, never a runtime mode.
        if transport_factory is None:
            from gz.transport13 import Node as GzNode
            transport_factory=GzNode
        from gz.msgs10.odometry_pb2 import Odometry as GzOdometry
        from gz.msgs10.twist_pb2 import Twist
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.actuators_pb2 import Actuators
        self._Twist,self._Boolean,self._Actuators=Twist,Boolean,Actuators
        self.gz=transport_factory();self.gz.subscribe(GzOdometry,f'/{self.vehicle}/physics/odometry',self._on_physics)
        self._commands=self.gz.advertise(f'/{self.vehicle}/command/twist',Twist)
        self._enable=self.gz.advertise(f'/{self.vehicle}/enable',Boolean)
        self._motors=self.gz.advertise(f'/{self.vehicle}/command/motor_speed',Actuators)
        if self.count_publishers(f'/{self.vehicle}/odom'):
            raise RuntimeError('another scout odometry authority exists')
        self._odom=self.create_publisher(Odometry,f'/{self.vehicle}/odom',STATE_QOS)
        self._evidence=self.create_publisher(EvidenceRecord,'/redline/evidence',EVENT_QOS)
        self._status=self.create_publisher(String,f'/{self.vehicle}/flight_state',STATE_QOS)
        self._tf=TransformBroadcaster(self);self._static=StaticTransformBroadcaster(self)
        transform=TransformStamped();transform.header.frame_id='map';transform.child_frame_id=f'{self.vehicle}/odom'
        transform.transform.translation.x,transform.transform.translation.y,transform.transform.translation.z=map(float,self.origin)
        transform.transform.rotation.w=1.;self._static.sendTransform(transform)
        self.create_timer(.05,self._publish_pose,clock=Clock(clock_type=ClockType.STEADY_TIME))
        self._server=ActionServer(self,ExecuteScout,f'/{self.vehicle}/execute_scout',self._execute,
            goal_callback=self._accept,cancel_callback=lambda _:CancelResponse.ACCEPT,callback_group=ReentrantCallbackGroup())
        self.get_logger().warning('SCENARIO physical scout; Gazebo feedback control, '+
            ('SIMULATED truth observation adapter enabled' if self.truth else 'perception absent; flight-only results are PARTIAL'))

    def _on_phase(self,message):
        with self._lock:self._phase,self._phase_receipt=message.phase,time.monotonic()

    def _on_crew(self,crew,message):
        p=message.pose.position
        with self._lock:
            if message.header.frame_id=='map' and all(math.isfinite(v) for v in (p.x,p.y,p.z)):
                self._crew[crew]=((p.x,p.y,p.z),time.monotonic())
            else:self._crew.pop(crew,None)

    def _on_physics(self,message):
        p,q,v=message.pose.position,message.pose.orientation,message.twist.linear
        xyz=(p.x,p.y,p.z);quat=(q.x,q.y,q.z,q.w);velocity=(v.x,v.y,v.z)
        if not all(math.isfinite(t) for t in xyz+quat+velocity):return
        if abs(sum(t*t for t in quat)-1)>1e-3:return
        value=PhysicsPose(message.header.stamp.sec+message.header.stamp.nsec*1e-9,xyz,quat,velocity,time.monotonic())
        with self._lock:self._pose=value

    def _safe(self, *, require_phase=True):
        with self._lock:
            now=time.monotonic();pose=self._pose
            if pose is None or not 0<=now-pose.received<=1:return False,'physical odometry stale/missing'
            if require_phase and (self._phase!=MissionState.PRECURSOR or not 0<=now-self._phase_receipt<=self.max_age):
                return False,'fresh PRECURSOR required'
            for crew in self.crew_ids:
                data=self._crew.get(crew)
                if data is None or not 0<=now-data[1]<=self.max_age:return False,f'{crew} position stale/missing'
                if math.dist(pose.xyz,data[0])<self.separation+3:return False,f'FR-14 separation from {crew}'
            if math.hypot(pose.xyz[0]-self.origin[0],pose.xyz[1]-self.origin[1])>self.max_distance+5:
                return False,'flight range exceeded'
        return True,''

    def _accept(self,goal):
        safe,reason=self._safe()
        points=[(p.x,p.y) for p in goal.corridor.points]
        valid=(goal.vehicle_id==self.vehicle and goal.request_id and len(goal.request_id)<=160 and
            len(points)>=3 and len(points)<=64 and all(math.isfinite(v) for xy in points for v in xy) and
            math.isfinite(goal.altitude_m) and 2<=goal.altitude_m<=30 and math.isfinite(goal.max_flight_s) and
            0<=goal.max_flight_s<=self.max_flight and all(math.hypot(x-self.origin[0],y-self.origin[1])<=self.max_distance for x,y in points))
        with self._lock:
            if not safe or not valid or self._busy or goal.request_id in self._seen:
                self.get_logger().warning('physical scout request rejected: '+(reason or 'invalid/duplicate/busy goal'))
                return GoalResponse.REJECT
            self._busy=True;self._seen.add(goal.request_id)
        return GoalResponse.ACCEPT

    def _publish_pose(self):
        with self._lock:pose=self._pose
        if not pose or pose.stamp_s<=self._last_published or time.monotonic()-pose.received>1:return
        self._last_published=pose.stamp_s
        message=Odometry();message.header.frame_id=f'{self.vehicle}/odom';message.child_frame_id=f'{self.vehicle}/base_link'
        message.header.stamp.sec=int(pose.stamp_s);message.header.stamp.nanosec=int((pose.stamp_s-int(pose.stamp_s))*1e9)
        message.pose.pose.position.x,message.pose.pose.position.y,message.pose.pose.position.z=(p-o for p,o in zip(pose.xyz,self.origin))
        q=message.pose.pose.orientation;q.x,q.y,q.z,q.w=pose.quat
        message.twist.twist.linear.x,message.twist.twist.linear.y,message.twist.twist.linear.z=pose.velocity
        self._odom.publish(message)
        elapsed=max(0.,pose.stamp_s-self._flight_start) if self._flight_start is not None else 0.
        self._status.publish(String(data=json.dumps({'schema':'redline.scout.flight.v1','physical_backend':True,
            'request_id':self._request_id,'phase':self._flight_stage,'progress':self._flight_progress,
            'map_xyz_m':pose.xyz,'battery_wh':max(0.,self.battery-self.power*elapsed/3600),
            'flight_s':elapsed,'observation_backend':'SIMULATED truth adapter' if self.truth else 'ABSENT'})))
        transform=TransformStamped();transform.header=message.header;transform.child_frame_id=message.child_frame_id
        p=message.pose.pose.position;transform.transform.translation.x,transform.transform.translation.y,transform.transform.translation.z=p.x,p.y,p.z
        transform.transform.rotation=q;self._tf.sendTransform(transform)

    def _command(self,world_velocity):
        with self._lock:pose=self._pose
        message=self._Twist()
        if pose:
            # Gazebo's Lee velocity controller multiplies all three body axes
            # by the full attitude R. Yaw-only inversion destabilizes a tilted
            # climb and made waypoint corners bank by >50 degrees in BXW.
            message.linear.x,message.linear.y,message.linear.z=world_to_body_velocity(world_velocity,pose.quat)
        self._commands.publish(message)

    def _ground(self,x,y):
        if self.grid:
            try:return float(self.grid.layer('z_m')[self.grid.cell_index(x,y)])
            except ValueError:raise RuntimeError('flight target outside known terrain grid')
        return self.ground

    def _goto(self,target,phase,handle,flight_start,wall_start,limit,tolerance=.7):
        initial_distance=None
        self._flight_stage=phase
        while rclpy.ok():
            if handle.is_cancel_requested:return 'canceled'
            safe,reason=self._safe()
            if not safe:raise RuntimeError(reason)
            with self._lock:pose=self._pose
            elapsed=pose.stamp_s-flight_start
            if elapsed>limit or time.monotonic()-wall_start>limit*1.5+20:raise RuntimeError('physical flight deadline exceeded')
            if self.power*elapsed/3600>self.battery*.8:raise RuntimeError('SCENARIO battery reserve reached')
            delta=tuple(t-p for t,p in zip(target,pose.xyz));distance=math.sqrt(sum(v*v for v in delta))
            if initial_distance is None:initial_distance=max(distance,tolerance)
            self._flight_progress=max(self._flight_progress,self._progress_base+self._progress_span*max(0.,min(1.,1-distance/initial_distance)))
            # Require a settled vehicle, not merely a fast pass through the
            # waypoint tolerance; physical speed remains the measured source.
            if distance<tolerance and math.sqrt(sum(v*v for v in pose.velocity))<.3:return None
            dt=0. if self._setpoint_stamp is None else pose.stamp_s-self._setpoint_stamp
            if dt<0:raise RuntimeError('physical control timestep rewound')
            # Observation/product work between waypoints can exceed a control
            # interval. Fresh odometry is checked by _safe; limit the next
            # integration step instead of allowing a large velocity jump.
            dt=min(dt,.1)
            velocity=flight_velocity_setpoint(delta,self._setpoint,dt,speed=self.speed,
                horizontal_accel=self.command_accel,vertical_accel=self.vertical_accel)
            self._setpoint,self._setpoint_stamp=velocity,pose.stamp_s
            # Check one braking interval ahead, not only the current position.
            predicted=tuple(p+.6*v for p,v in zip(pose.xyz,velocity))
            with self._lock:
                if any(math.dist(predicted,p)<self.separation+3 for p,receipt in self._crew.values()):
                    raise RuntimeError('FR-14 predicted separation would be violated')
            self._command(velocity)
            feedback=ExecuteScout.Feedback();feedback.phase=phase;feedback.battery_wh=max(0.,self.battery-self.power*elapsed/3600)
            handle.publish_feedback(feedback);time.sleep(.05)
        raise RuntimeError('ROS shutdown during physical flight')

    def _observe(self,request_id):
        if not self.truth:return
        with self._lock:pose=self._pose
        x,y,_=pose.xyz;r=self.spacing/2
        patch=[(x-r,y-r),(x+r,y-r),(x+r,y+r),(x-r,y+r)]
        for px,py,radius,passable in survey_evidence(self.truth,self.grid,patch,spacing_m=self.spacing,detection_limit_m=1.,d_block_m=2.):
            key=(self.grid.cell_index(px,py),passable)
            if key in self._evidence_keys:continue
            self._evidence_keys.add(key);record=EvidenceRecord();record.header.frame_id='map'
            record.header.stamp.sec=int(pose.stamp_s);record.header.stamp.nanosec=int((pose.stamp_s-int(pose.stamp_s))*1e9)
            record.measured=record.received=record.header.stamp;record.evidence_id=f'{request_id}-{len(self._evidence_ids):04d}'
            record.source='scout_flight_simulated_observer';record.provenance.status=Provenance.SIMULATED
            record.provenance.note='SCENARIO truth adapter at actual Gazebo flight waypoint; NOT camera/LiDAR sensing'
            record.pose.pose.position.x,record.pose.pose.position.y=px,py;record.pose.pose.orientation.w=1.
            record.resolution_m=float(self.grid.resolution_m);record.quality=1.
            obs={'schema':'redline.cell_observation.v2','state':'DETECTED','radius_m':radius}
            if not passable:obs['passable']=False
            record.summary_json=json.dumps({'cell_observation':obs});self._evidence.publish(record);self._evidence_ids.append(record.evidence_id)

    def _execute(self,handle):
        goal=handle.request;start=time.monotonic();self._evidence_ids=[];self._evidence_keys=set()
        self._request_id=goal.request_id;self._flight_progress=0.
        with self._lock:flight_start=self._pose.stamp_s
        self._flight_start=flight_start
        self._setpoint=(0.,0.,0.);self._setpoint_stamp=flight_start
        result=ExecuteScout.Result();limit=goal.max_flight_s or self.max_flight
        try:
            enabled=self._Boolean();enabled.data=True;self._enable.publish(enabled)
            points=[(p.x,p.y) for p in goal.corridor.points]
            # Each requested polygon edge is sampled at <=survey_spacing. This
            # is a perimeter inspection, not a claimed full raster coverage.
            route=[]
            for a,b in zip(points,points[1:]+points[:1]):
                n=max(1,int(math.ceil(math.dist(a,b)/self.spacing)))
                route.extend((a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n) for i in range(n))
            altitude=float(goal.altitude_m)
            self._progress_base=0.;self._progress_span=1./(len(route)+3)
            canceled=self._goto((self.origin[0],self.origin[1],self.ground+altitude),'TAKEOFF',handle,flight_start,start,limit)
            for i,(x,y) in enumerate(route):
                if canceled:break
                self._progress_base=(i+1)/(len(route)+3)
                canceled=self._goto((x,y,self._ground(x,y)+altitude),'TRANSIT' if i==0 else 'SURVEY',handle,flight_start,start,limit)
                if not canceled:self._observe(goal.request_id)
            if not canceled:
                self._progress_base=(len(route)+1)/(len(route)+3)
                canceled=self._goto((self.origin[0],self.origin[1],self.ground+altitude),'RETURN',handle,flight_start,start,limit)
                if not canceled:
                    self._progress_base=(len(route)+2)/(len(route)+3)
                    canceled=self._goto((self.origin[0],self.origin[1],self.ground+.08),'LANDING',handle,flight_start,start,limit,tolerance=.12)
            if canceled:
                handle.canceled();result.outcome=result.CANCELED;result.reason='canceled; physical controller holds position'
            else:
                handle.succeed();result.outcome=result.SUCCEEDED if self._evidence_ids else result.PARTIAL
                result.reason='physical perimeter flight; SIMULATED observation adapter' if self._evidence_ids else 'physical flight complete; perception absent, no evidence'
        except Exception as error:
            self.get_logger().error('physical scout stopped: '+str(error))
            if handle.is_active:handle.abort()
            result.outcome=result.FAILED;result.reason=str(error)
        finally:
            self._command((0,0,0))
            self._flight_stage='COMPLETE' if result.outcome in (result.SUCCEEDED,result.PARTIAL) else 'STOPPED'
            if result.outcome in (result.SUCCEEDED,result.PARTIAL):self._flight_progress=1.
            with self._lock:
                pose=self._pose;self._busy=False
            result.flight_s=max(0.,pose.stamp_s-flight_start) if pose else 0.
            result.battery_used_wh=self.power*result.flight_s/3600;result.evidence_ids=list(self._evidence_ids)
            self.battery=max(0.,self.battery-result.battery_used_wh);self._flight_start=None
        return result

    def destroy_node(self):
        if hasattr(self,'_commands'):self._command((0,0,0))
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args);node=ScoutFlightNode();executor=MultiThreadedExecutor();executor.add_node(node)
    try:executor.spin()
    except (KeyboardInterrupt,ExternalShutdownException):pass
    finally:executor.shutdown();node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
