#!/usr/bin/env python3
"""Read-only static TF bridge snapshot; NOT a new /tf or /tf_static authority.

rosbridge 2.7.1's new-client transient replay releases its temporary subscriber
after the first writer sample. RSP and map->odom use different writers. This
adapter caches every observed static edge and publishes one combined message
on a dedicated bridge topic, preserving all source frame IDs and timestamps.
"""
import json
import math
from collections import OrderedDict
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
from tf2_msgs.msg import TFMessage
from std_msgs.msg import String


class StaticSnapshot(Node):
    def __init__(self):
        super().__init__('redline_bridge_static_snapshot')
        qos=QoSProfile(depth=100,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
        self.edges=OrderedDict();self.parents={};self.invalid=False
        self.pub=self.create_publisher(TFMessage,'/redline/bridge/tf_static_snapshot',qos)
        self.status=self.create_publisher(String,'/redline/bridge/tf_static_snapshot_status',qos)
        self.sub=self.create_subscription(TFMessage,'/tf_static',self.receive,qos)

    def receive(self,message):
        for edge in message.transforms:
            parent,child=edge.header.frame_id,edge.child_frame_id
            t,q=edge.transform.translation,edge.transform.rotation
            finite=all(math.isfinite(v) for v in (t.x,t.y,t.z,q.x,q.y,q.z,q.w))
            norm=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w
            if not parent or not child or parent==child or not finite or abs(norm-1)>.001:
                self.invalid=True
            if child in self.parents and self.parents[child]!=parent:self.invalid=True
            self.parents[child]=parent;self.edges[(parent,child)]=edge
        status=String();status.data=json.dumps({'valid':not self.invalid,'edges':len(self.edges),
            'topic':'/redline/bridge/tf_static_snapshot','authority':'source ROS static broadcasters; bridge cache only'})
        self.status.publish(status)
        if not self.invalid:
            result=TFMessage();result.transforms=list(self.edges.values());self.pub.publish(result)


def main():
    rclpy.init();node=StaticSnapshot()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
