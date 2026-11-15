"""Read-only TF adapter: actual rover odometry -> map-frame science pose.

Never publishes /tf, robot odometry or commands. Stale inputs stop publication.
"""
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from tf2_ros import Buffer, TransformListener, TransformException
from tf2_geometry_msgs import do_transform_pose


class CampaignRobotPose(Node):
    def __init__(self, **kwargs):
        super().__init__("campaign_robot_pose", **kwargs)
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.publisher = self.create_publisher(PoseStamped, "/redline/science/rover_pose", 10)
        self.create_subscription(Odometry, "/rover_1/odom", self.receive, qos_profile_sensor_data)

    def receive(self, msg):
        if msg.header.frame_id not in ("rover_1/odom", "map") or msg.child_frame_id != "rover_1/base_link":
            return
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        if not all(math.isfinite(v) for v in (p.x, p.y, p.z, q.x, q.y, q.z, q.w)):
            return
        if abs(sum(v*v for v in (q.x,q.y,q.z,q.w))-1) > .01:
            return
        stamp = Time.from_msg(msg.header.stamp)
        if abs((self.get_clock().now()-stamp).nanoseconds*1e-9) > 1:
            return
        result = PoseStamped()
        result.header.frame_id, result.header.stamp = "map", msg.header.stamp
        if msg.header.frame_id == "map":
            result.pose = msg.pose.pose
        else:
            try:
                transform = self.buffer.lookup_transform("map", msg.header.frame_id, stamp)
                result.pose = do_transform_pose(msg.pose.pose, transform)
            except TransformException:
                return
        self.publisher.publish(result)


def main(args=None):
    rclpy.init(args=args)
    node = CampaignRobotPose()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
