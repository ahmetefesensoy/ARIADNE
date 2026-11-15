#!/usr/bin/env python3
"""Stationary measured-cloud probe. Fixture geometry is evaluation-only."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import time
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2,LaserScan
from sensor_msgs_py import point_cloud2
from std_msgs.msg import String


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();rclpy.init();node=rclpy.create_node('t3_perception_probe')
    data={'created_at_utc':datetime.now(timezone.utc).isoformat(),'evaluation_only':True,'passed':False,
          'raw_cloud_count':0,'valid_segmentations':0,'invalid_reasons':{},'max_ground_points':0,
          'max_obstacle_points':0,'max_processing_ms':0,'low_fixture_returns':0,'raw_2d_finite_max':0}
    saved={};subs=[]
    def cloud(msg,kind):
        points=point_cloud2.read_points_numpy(msg,field_names=['x','y','z'],skip_nans=False).reshape(-1,3)
        finite=points[np.isfinite(points).all(axis=1)]
        saved[kind]=finite
        if kind=='raw':
            data['raw_cloud_count']+=1;data['raw_dimensions']=[msg.width,msg.height]
            if len(finite):data['raw_z_extent_m']=[float(finite[:,2].min()),float(finite[:,2].max())]
        elif kind=='obstacles' and len(finite):
            # Read-only truth comparison: never sent to the filter/planner.
            roi=finite[(finite[:,0]>4.0)&(finite[:,0]<6)&(np.abs(finite[:,1])<.8)&(finite[:,2]<-1.5)]
            data['low_fixture_returns']=max(data['low_fixture_returns'],len(roi))
            if len(roi):data['fixture_points_sensor_xyz_m']=roi[:20].tolist()
    def status(msg):
        value=json.loads(msg.data)
        if value['valid']:
            data['valid_segmentations']+=1
            for key in ('ground_points','obstacle_points'):data['max_'+key]=max(data['max_'+key],value[key])
            data['last_plane_z_abc']=value['plane_z_abc'];data['last_fit_rms_m']=value['fit_rms_m']
        else:
            reason=value.get('reason','unknown');data['invalid_reasons'][reason]=data['invalid_reasons'].get(reason,0)+1
        data['max_processing_ms']=max(data['max_processing_ms'],value['processing_wall_ms'])
    for topic,kind in (('lidar_3d/points','raw'),('lidar/ground','ground'),('lidar/obstacles','obstacles')):
        subs.append(node.create_subscription(PointCloud2,'/rover_1/'+topic,lambda msg,k=kind:cloud(msg,k),qos_profile_sensor_data))
    subs.append(node.create_subscription(String,'/rover_1/lidar/segmentation_status',status,10))
    def scan(msg):data['raw_2d_finite_max']=max(data['raw_2d_finite_max'],int(np.isfinite(msg.ranges).sum()))
    subs.append(node.create_subscription(LaserScan,'/rover_1/scan',scan,qos_profile_sensor_data))
    try:
        end=time.monotonic()+50;first_valid=None
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.1)
            if data['valid_segmentations']>=3 and first_valid is None:first_valid=time.monotonic()
            if first_valid is not None and time.monotonic()-first_valid>3:break
        data['passed']=data['valid_segmentations']>=3 and data['raw_cloud_count']>=3 and data['low_fixture_returns']>=2
    except Exception as error:data['error']=str(error)
    finally:
        node.destroy_node();rclpy.try_shutdown()
        np.savez_compressed(args.out.with_suffix('.npz'),**saved)
        data['limits']=['Stationary low SCENARIO box detection, not general terrain classification or autonomous avoidance.',
                        'Expected box region is used only here for evaluation, never in the segmentation node.']
        args.out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data,indent=2))
    return 0 if data['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
