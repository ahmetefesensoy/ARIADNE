"""Actual DDS odometry + static TF -> science pose; no actuator commands."""
import math
import time
import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import Odometry
from rclpy.executors import SingleThreadedExecutor
from tf2_ros import StaticTransformBroadcaster
from redline_mission.campaign_robot_pose import CampaignRobotPose


def test_map_pose_requires_fresh_valid_odometry_and_applies_actual_tf():
    rclpy.init()
    adapter = CampaignRobotPose()
    probe = rclpy.create_node("campaign_pose_probe")
    publisher = probe.create_publisher(Odometry, "/rover_1/odom", 10)
    received = []
    probe.create_subscription(PoseStamped, "/redline/science/rover_pose", received.append, 10)
    broadcaster = StaticTransformBroadcaster(probe)
    tf = TransformStamped()
    tf.header.frame_id, tf.child_frame_id = "map", "rover_1/odom"
    tf.transform.translation.x, tf.transform.translation.y, tf.transform.translation.z = 10., 20., 30.
    tf.transform.rotation.z, tf.transform.rotation.w = math.sin(math.pi/4), math.cos(math.pi/4)
    broadcaster.sendTransform(tf)
    executor = SingleThreadedExecutor()
    for node in (adapter, probe): executor.add_node(node)
    def spin(seconds):
        stop = time.monotonic() + seconds
        while time.monotonic() < stop: executor.spin_once(timeout_sec=.01)
    try:
        spin(.4)
        msg = Odometry()
        msg.header.frame_id, msg.child_frame_id = "rover_1/odom", "rover_1/base_link"
        msg.header.stamp = probe.get_clock().now().to_msg()
        msg.pose.pose.position.x = 2.
        msg.pose.pose.orientation.w = 1.
        publisher.publish(msg); spin(.4)
        assert received
        p = received[-1].pose.position
        assert abs(p.x-10) < 1e-6 and abs(p.y-22) < 1e-6 and abs(p.z-30) < 1e-6
        assert received[-1].header.frame_id == "map"
        count = len(received)
        msg.header.stamp.sec -= 10
        publisher.publish(msg); spin(.15)
        msg.header.stamp = probe.get_clock().now().to_msg()
        msg.header.frame_id = "untrusted_origin"
        publisher.publish(msg); spin(.15)
        msg.header.frame_id = "rover_1/odom"
        msg.pose.pose.orientation.w = 0.
        publisher.publish(msg); spin(.15)
        assert len(received) == count
    finally:
        executor.shutdown()
        for node in (adapter, probe): node.destroy_node()
        rclpy.try_shutdown()
