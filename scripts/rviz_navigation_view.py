#!/usr/bin/env python3
"""Diagnostic copies of planar Nav2 drawings at the Mars inspection elevation.

No command, goal, planning, odometry or original map publishers. The new static
frame lets RViz's XY-plane goal tool select the local Mars surface rather than
the distant map z=0 plane. Original negative map elevations remain unchanged.
"""
import argparse
from copy import deepcopy
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from geometry_msgs.msg import PolygonStamped, TransformStamped
from nav_msgs.msg import OccupancyGrid, Path
from map_msgs.msg import OccupancyGridUpdate
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster


VIEW_FRAME = 'redline/navigation_view'


def at_inspection_height(message, height):
    """Copy only map-frame 2D drawing elevations; never mutate Nav2 input."""
    if not math.isfinite(height):
        raise ValueError('Inspection elevation must be finite')
    if message.header.frame_id != 'map':
        raise ValueError('Only map-frame diagnostic drawings are supported')
    result = deepcopy(message)
    if isinstance(result, OccupancyGrid):
        result.info.origin.position.z = height
    elif isinstance(result, Path):
        for pose in result.poses:
            if pose.header.frame_id not in ('', 'map'):
                raise ValueError('Path contains a different frame')
            pose.pose.position.z = height + 0.15
    elif isinstance(result, PolygonStamped):
        for point in result.polygon.points:
            point.z = height + 0.12
    elif not isinstance(result, OccupancyGridUpdate):
        raise TypeError(type(result).__name__)
    return result


class NavigationView(Node):
    def __init__(self, height):
        super().__init__('rviz_navigation_view')
        if not math.isfinite(height):
            raise ValueError('Inspection elevation must be finite')
        self.height = height
        self.static = StaticTransformBroadcaster(self)
        frame = TransformStamped()
        frame.header.stamp = self.get_clock().now().to_msg()
        frame.header.frame_id = 'map'
        frame.child_frame_id = VIEW_FRAME
        frame.transform.translation.z = height
        frame.transform.rotation.w = 1.0
        self.static.sendTransform(frame)
        durable = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.connections = []
        specs = [(Path, 'plan', 10)]
        # Local costmap already uses the correctly elevated odom frame. Robot
        # polygons also carry their own physical TF; RViz consumes them directly.
        for source in ('map', 'global_costmap/costmap'):
            specs.append((OccupancyGrid, source, durable))
            if source != 'map':
                specs.append((OccupancyGridUpdate, source + '_updates', 10))
        for kind, source, qos in specs:
            publisher = self.create_publisher(kind, '/redline/view/' + source, qos)
            def receive(message, pub=publisher):
                try:
                    pub.publish(at_inspection_height(message, self.height))
                except (ValueError, TypeError) as error:
                    self.get_logger().warning(str(error))
            self.connections.append(self.create_subscription(kind, '/rover_1/' + source, receive, qos))
        self.get_logger().info(f'Display-only plane z={height}; goal projection frame={VIEW_FRAME}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--height', type=float, required=True)
    args, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    node = NavigationView(args.height)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
