"""Run the real C++ observer on isolated, non-command topics (ROS domain 79)."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from ament_index_python.packages import get_package_prefix
from geometry_msgs.msg import PoseStamped
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String


def test_actual_rmw_writer_gid_and_original_pose_are_required_for_evidence():
    topic='/redline/t3/test_goal_pose';evidence_topic='/redline/t3/test_goal_evidence'
    executable=Path(get_package_prefix('redline_bringup'))/'lib/redline_bringup/rviz_goal_observer'
    env=dict(os.environ,ROS_DOMAIN_ID='79')
    process=subprocess.Popen([str(executable),'--ros-args','-p','goal_topic:='+topic,
        '-p','evidence_topic:='+evidence_topic],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    context=Context();rclpy.init(context=context,domain_id=79)
    listener=Node('scripted_goal',context=context)
    rviz=Node('rviz_navigation',namespace='/rover_1',context=context)
    executor=SingleThreadedExecutor(context=context);executor.add_node(listener)
    samples=[]
    subscription=listener.create_subscription(String,evidence_topic,lambda m:samples.append(json.loads(m.data)),10)
    wrong=listener.create_publisher(PoseStamped,topic,10)
    correct=rviz.create_publisher(PoseStamped,topic,10)

    def spin_until(predicate,seconds=8):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            assert process.poll() is None,'C++ observer exited before evidence'
            if predicate():return True
            executor.spin_once(timeout_sec=.05)
        return predicate()

    try:
        assert spin_until(lambda:wrong.get_subscription_count()>0 and correct.get_subscription_count()>0
                          and listener.count_publishers(evidence_topic)==1),'Observer discovery timed out'
        message=PoseStamped();message.header.frame_id='map'
        message.header.stamp.sec=12;message.header.stamp.nanosec=345
        message.pose.position.x=145.25;message.pose.position.y=-299.125
        message.pose.orientation.w=1.0
        wrong.publish(message)
        assert not spin_until(lambda:bool(samples),.6),'Unrelated writer was accepted as RViz'
        correct.publish(message)
        assert spin_until(lambda:bool(samples)),'Actual RViz writer did not produce evidence'
        value=samples[0]
        endpoint=next(e for e in listener.get_publishers_info_by_topic(topic) if e.node_name=='rviz_navigation')
        assert value['schema']=='redline.t3.rviz-goal.v1' and value['goal_topic']==topic
        assert value['publisher']=={'node_name':'rviz_navigation','node_namespace':'/rover_1',
                                    'publisher_gid':bytes(endpoint.endpoint_gid).hex()}
        assert value['source_timestamp_ns']>0
        assert value['pose']=={'stamp_sec':12,'stamp_nanosec':345,'frame_id':'map',
                               'position':[145.25,-299.125,0.0],'orientation':[0.0,0.0,0.0,1.0]}
        assert listener.count_publishers(topic)==2,'Observer must not republish or actuate a goal'
    finally:
        executor.shutdown();listener.destroy_subscription(subscription);listener.destroy_node();rviz.destroy_node()
        rclpy.shutdown(context=context)
        if process.poll() is None:process.send_signal(signal.SIGINT)
        try:output,_=process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill();output,_=process.communicate(timeout=3)
    assert process.returncode==0,output
