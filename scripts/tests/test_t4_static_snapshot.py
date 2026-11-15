"""Isolated real ROS adapter check; never uses live domain 77."""
import importlib.util
import os
from pathlib import Path
import time
import json
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage
from std_msgs.msg import String

spec=importlib.util.spec_from_file_location('static_snapshot',Path(__file__).parents[1]/'t4_static_tf_snapshot.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_two_transient_writers_become_one_complete_late_subscriber_snapshot():
    os.environ['ROS_DOMAIN_ID']='84'
    rclpy.init();node=m.StaticSnapshot();peer=rclpy.create_node('t4_static_snapshot_test_peer')
    qos=QoSProfile(depth=100,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
    first=peer.create_publisher(TFMessage,'/tf_static',qos);second=peer.create_publisher(TFMessage,'/tf_static',qos)
    executor=SingleThreadedExecutor();executor.add_node(node);executor.add_node(peer)
    def wait(predicate,seconds=3):
        end=time.monotonic()+seconds
        while not predicate() and time.monotonic()<end:executor.spin_once(timeout_sec=.02)
        assert predicate()
    def edge(parent,child,x):
        t=TransformStamped();t.header.frame_id=parent;t.child_frame_id=child
        t.transform.translation.x=float(x);t.transform.rotation.w=1.;return t
    try:
        wait(lambda:first.get_subscription_count()==1 and second.get_subscription_count()==1)
        for publisher,t in ((first,edge('map','rover_1/odom',145)),(second,edge('rover_1/base_link','rover_1/lidar_link',0))):
            message=TFMessage();message.transforms=[t];publisher.publish(message)
        wait(lambda:len(node.edges)==2)
        received=[]
        statuses=[]
        status_sub=peer.create_subscription(String,'/redline/bridge/tf_static_snapshot_status',lambda msg:statuses.append(json.loads(msg.data)),qos)
        sub=peer.create_subscription(TFMessage,'/redline/bridge/tf_static_snapshot',lambda msg:received.append(msg),qos)
        wait(lambda:any(len(msg.transforms)==2 for msg in received))
        assert any(t.header.frame_id=='map' and t.child_frame_id=='rover_1/odom' and t.transform.translation.x==145 for t in received[-1].transforms)
        # Cache is not another TF publisher: only the two test writers exist.
        assert peer.count_publishers('/tf_static')==2
        count=len(received);bad=TFMessage();bad.transforms=[edge('conflicting_parent','rover_1/odom',0)]
        first.publish(bad);wait(lambda:node.invalid)
        wait(lambda:any(not status['valid'] for status in statuses))
        end=time.monotonic()+.3
        while time.monotonic()<end:executor.spin_once(timeout_sec=.02)
        assert len(received)==count
        late_status=[]
        late=peer.create_subscription(String,'/redline/bridge/tf_static_snapshot_status',lambda msg:late_status.append(json.loads(msg.data)),qos)
        wait(lambda:any(not status['valid'] for status in late_status))
    finally:executor.shutdown();node.destroy_node();peer.destroy_node();rclpy.try_shutdown()
