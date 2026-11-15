"""Real rclpy adapter test: preserve stamps, reject stale/invalid/replayed data."""
import importlib.util
from pathlib import Path
import json
import time
import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header,String

spec=importlib.util.spec_from_file_location('ground_filter',Path(__file__).parents[1]/'scripts/ground_filter.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_live_cloud_adapter_never_clears_on_invalid_ground_or_stale_frames():
    rclpy.init();node=m.GroundFilter();peer=rclpy.create_node('ground_filter_test_peer')
    clouds=[];diagnostics=[]
    sub=peer.create_subscription(PointCloud2,'/rover_1/lidar/obstacles',lambda msg:clouds.append(msg),qos_profile_sensor_data)
    status=peer.create_subscription(String,'/rover_1/lidar/segmentation_status',lambda msg:diagnostics.append(json.loads(msg.data)),10)
    pub=peer.create_publisher(PointCloud2,'/rover_1/lidar_3d/points',qos_profile_sensor_data)
    executor=SingleThreadedExecutor();executor.add_node(node);executor.add_node(peer)
    def spin_until(predicate,seconds=3):
        end=time.monotonic()+seconds
        while time.monotonic()<end and not predicate():executor.spin_once(timeout_sec=.02)
        assert predicate()
    try:
        spin_until(lambda:pub.get_subscription_count()==1)
        x,y=np.meshgrid(np.linspace(-6,6,30),np.linspace(-6,6,30))
        floor=np.column_stack((x.ravel(),y.ravel(),np.full(x.size,-2.35)))
        rock=np.array([[4,.05*i,-2.05] for i in range(-4,5)])
        header=Header();header.frame_id='rover_1/lidar_link';header.stamp=peer.get_clock().now().to_msg()
        message=point_cloud2.create_cloud_xyz32(header,np.vstack((floor,rock)).astype(np.float32))
        pub.publish(message);spin_until(lambda:len(clouds)==1 and len(diagnostics)==1)
        assert diagnostics[-1]['valid'] and diagnostics[-1]['obstacle_points']==9
        assert clouds[-1].header==message.header and clouds[-1].width==9
        pub.publish(message);spin_until(lambda:len(diagnostics)==2)
        assert diagnostics[-1]['reason']=='repeated_or_reversed_stamp' and len(clouds)==1
        for frame,age,expected in (('wrong',0,'unexpected_sensor_frame'),('rover_1/lidar_link',2,'stale_or_future_input')):
            message.header.frame_id=frame;message.header.stamp=peer.get_clock().now().to_msg();message.header.stamp.sec-=age
            before=len(diagnostics);pub.publish(message);spin_until(lambda:len(diagnostics)>before)
            assert diagnostics[-1]['reason']==expected and len(clouds)==1
        message.header.stamp=peer.get_clock().now().to_msg()
        message=point_cloud2.create_cloud_xyz32(message.header,np.array([[1,0,-2.35]],dtype=np.float32))
        before=len(diagnostics);pub.publish(message);spin_until(lambda:len(diagnostics)>before)
        assert not diagnostics[-1]['valid'] and len(clouds)==1
    finally:executor.shutdown();node.destroy_node();peer.destroy_node();rclpy.try_shutdown()
