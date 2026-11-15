#!/usr/bin/env python3
"""Hold a read-only full navigation graph for integration consumers; no goal."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import rclpy


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--seconds',type=float,required=True);args=parser.parse_args()
    if not 1<=args.seconds<=3600:parser.error('hold must be in [1,3600] seconds')
    sys.path.insert(0,str(args.workspace/'install/redline_bringup/lib/redline_bringup'))
    from verify_navigation import Checker,measured_pose
    rclpy.init();node=Checker();report={'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'passed':False,'read_only':True,'mode':'stationary full-graph hold; no NavigateToPose goal or velocity publisher'}
    try:
        if not node.wait(lambda:len(node.counts)==5 and min(node.counts.values())>=2,45):raise RuntimeError('Missing sensors/localization')
        if not node.wait_active():raise RuntimeError('Nav2 not active')
        report['start_physical_xyz']=measured_pose()
        print(json.dumps({'event':'stationary_graph_ready','hold_seconds':args.seconds}),flush=True)
        node.wait(lambda:False,args.seconds)
        report['end_physical_xyz']=measured_pose();report['sensor_counts']=dict(node.counts)
        report['passed']=True
    except Exception as error:report['error']=str(error)
    finally:
        node.destroy_node();rclpy.try_shutdown();report['ended_at_utc']=datetime.now(timezone.utc).isoformat()
        args.out.write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
