#!/usr/bin/env python3
"""Measured-only XYZ segmentation adapter. Classification lives in redline_core."""
import json
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import String
from redline_core.ground import GroundConfig,segment_ground


class GroundFilter(Node):
    def __init__(self):
        super().__init__('ground_filter',namespace='rover_1')
        defaults={'frame':'rover_1/lidar_link','expected_ground_z_m':-2.35,
                  'self_bounds':[-1.4,-1.4,-2.4,2.4,1.4,-.1],
                  'maximum_age_s':.5,'fit_radius_m':8.,'ground_tolerance_m':.08,
                  'obstacle_height_m':.14,'max_obstacle_height_m':3.,'max_slope_deg':20.,
                  'intercept_tolerance_m':.5,'minimum_support':40,'minimum_support_fraction':.45,
                  'trials':64,'seed':417,'local_surface_radius_m':1.5}
        values={k:self.declare_parameter(k,v).value for k,v in defaults.items()}
        self.frame=values.pop('frame');self.age_limit=values.pop('maximum_age_s')
        self.bounds=np.array(values.pop('self_bounds'),dtype=float).reshape(2,3)
        if not np.isfinite(self.bounds).all() or np.any(self.bounds[0]>=self.bounds[1]):raise ValueError('Invalid self bounds')
        self.config=GroundConfig(**values)
        self.last_stamp=None
        self.ground=self.create_publisher(PointCloud2,'lidar/ground',qos_profile_sensor_data)
        self.obstacles=self.create_publisher(PointCloud2,'lidar/obstacles',qos_profile_sensor_data)
        self.diagnostics=self.create_publisher(String,'lidar/segmentation_status',10)
        self.sub=self.create_subscription(PointCloud2,'lidar_3d/points',self.receive,qos_profile_sensor_data)

    def receive(self,message):
        started=time.monotonic();report={'status':'SIMULATED','valid':False,'input_frame':message.header.frame_id,
            'stamp_sec':message.header.stamp.sec,'stamp_nanosec':message.header.stamp.nanosec}
        try:
            stamp=message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec
            age=(self.get_clock().now().nanoseconds-stamp)/1e9
            if message.header.frame_id!=self.frame:raise ValueError('unexpected_sensor_frame')
            if not 0<=age<=self.age_limit:raise ValueError('stale_or_future_input')
            if self.last_stamp is not None and stamp<=self.last_stamp:raise ValueError('repeated_or_reversed_stamp')
            self.last_stamp=stamp
            # Jazzy read_points honours field offsets/endian. Skip invalids here
            # explicitly as sensors may label a cloud dense despite infinite rays.
            points=point_cloud2.read_points_numpy(message,field_names=['x','y','z'],skip_nans=False).reshape(-1,3)
            result=segment_ground(points,self.config,self_bounds=self.bounds)
            report.update(valid=result.valid,reason=result.reason,input_points=len(points),
                          finite_points=int(np.isfinite(points).all(axis=1).sum()),
                          ground_points=int(result.ground.sum()),obstacle_points=int(result.obstacles.sum()),
                          unknown_points=int(result.unknown.sum()),plane_z_abc=result.plane_z_abc,
                          support_fraction=result.support_fraction,fit_rms_m=result.fit_rms_m)
            if result.valid:
                for publisher,mask in ((self.ground,result.ground),(self.obstacles,result.obstacles)):
                    # Preserve measurement stamp/frame. Never publish a fresh
                    # empty obstacle cloud when plane fitting failed.
                    publisher.publish(point_cloud2.create_cloud_xyz32(message.header,points[mask].astype(np.float32)))
        except (ValueError,TypeError,AssertionError,RuntimeError) as error:report.update(reason=str(error))
        report['processing_wall_ms']=(time.monotonic()-started)*1000
        output=String();output.data=json.dumps(report);self.diagnostics.publish(output)


def main():
    rclpy.init();node=GroundFilter()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
