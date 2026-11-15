"""Real Nav2 integration: low commands, absolute cap, STOP, missing source."""
from pathlib import Path
import os
import signal
import subprocess
import time
import pytest
import rclpy
import yaml
from ament_index_python.packages import get_package_prefix
from geometry_msgs.msg import TransformStamped,Twist
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from sensor_msgs.msg import LaserScan
from tf2_ros import StaticTransformBroadcaster


def test_absolute_cap_preserves_low_commands_and_stop_guards(tmp_path):
    prefix='/collision_limit_regression';name='collision_limit_probe'
    polygon=lambda half: str([[half,half],[half,-half],[-half,-half],[-half,half]])
    params={'use_sim_time':False,'base_frame_id':'base_limit_probe','odom_frame_id':'odom_limit_probe',
        'enable_stamped_cmd_vel':False,'cmd_vel_in_topic':'cmd_in','cmd_vel_out_topic':'cmd_out',
        'transform_tolerance':.3,'source_timeout':.5,'base_shift_correction':False,'stop_pub_timeout':2.0,
        'polygons':['Stop','Limit'],
        'Stop':{'type':'polygon','points':polygon(.8),'action_type':'stop','min_points':1,'visualize':False},
        'Limit':{'type':'polygon','points':polygon(2.0),'action_type':'limit','linear_limit':.12,
                 'angular_limit':.12,'min_points':1,'visualize':False},
        'observation_sources':['scan'],'scan':{'type':'scan','topic':prefix+'/scan','source_timeout':.5,'enabled':True}}
    config=tmp_path/'params.yaml';config.write_text(yaml.safe_dump({prefix+'/'+name:{'ros__parameters':params}}))
    binary=Path(get_package_prefix('nav2_collision_monitor'))/'lib/nav2_collision_monitor/collision_monitor'
    logfile=tmp_path/'node.log';log=logfile.open('w')
    process=subprocess.Popen([str(binary),'--ros-args','-r','__node:='+name,'-r','__ns:='+prefix,'--params-file',str(config)],
                             stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    rclpy.init();peer=rclpy.create_node('collision_limit_test_peer');observed=[]
    sub=peer.create_subscription(Twist,prefix+'/cmd_out',lambda m:observed.append((m.linear.x,m.angular.z)),10)
    pub=peer.create_publisher(Twist,prefix+'/cmd_in',10);scan_pub=peer.create_publisher(LaserScan,prefix+'/scan',10)
    broadcaster=StaticTransformBroadcaster(peer);tf=TransformStamped()
    tf.header.stamp=peer.get_clock().now().to_msg();tf.header.frame_id='odom_limit_probe'
    tf.child_frame_id='base_limit_probe';tf.transform.rotation.w=1.;broadcaster.sendTransform(tf)

    def wait(predicate,seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if predicate():return True
            rclpy.spin_once(peer,timeout_sec=.02)
        return predicate()

    def phase(distance,velocity,seconds=.8):
        observed.clear();deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if distance is not None:
                scan=LaserScan();scan.header.stamp=peer.get_clock().now().to_msg();scan.header.frame_id='base_limit_probe'
                scan.angle_increment=1.;scan.range_min=.1;scan.range_max=10.;scan.ranges=[float(distance)]
                scan_pub.publish(scan)
            command=Twist();command.linear.x=velocity;command.angular.z=velocity;pub.publish(command)
            rclpy.spin_once(peer,timeout_sec=.03)
        return observed[-3:]

    try:
        service=peer.create_client(ChangeState,prefix+'/'+name+'/change_state')
        assert service.wait_for_service(timeout_sec=6),logfile.read_text()
        for transition in (Transition.TRANSITION_CONFIGURE,Transition.TRANSITION_ACTIVATE):
            request=ChangeState.Request();request.transition.id=transition
            future=service.call_async(request)
            assert wait(future.done,4) and future.result().success,logfile.read_text()
        assert wait(lambda:pub.get_subscription_count()>0 and scan_pub.get_subscription_count()>0,3)
        for velocity,expected in ((.3,.12),(.02,.02)):
            values=phase(1.5,velocity)
            assert len(values)==3
            for value in values:assert value==pytest.approx((expected,expected))
        assert phase(.5,.3)==[(0.,0.)]*3
        phase(1.5,.3,.3)
        assert phase(None,.3,1.0)==[(0.,0.)]*3
    finally:
        peer.destroy_node();rclpy.try_shutdown()
        if process.poll() is None:process.send_signal(signal.SIGINT)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        log.close()
    assert process.returncode==0,logfile.read_text()
