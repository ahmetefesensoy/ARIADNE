"""Isolated actual ExecuteScout/Gazebo flight, no camera/truth observation adapter.

Tests negative Mars elevation, TF/odom, physical takeoff/perimeter/landing and
PARTIAL semantics when perception is absent. Crew is an explicit test fixture.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time
import xml.etree.ElementTree as ET


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--out",required=True,type=Path)
    parser.add_argument('--domain',type=int,default=187)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    os.environ["GZ_PARTITION"]="redline-flight-action-"+str(os.getpid())
    os.environ["ROS_DOMAIN_ID"]=str(args.domain);os.environ["ROS_AUTOMATIC_DISCOVERY_RANGE"]="LOCALHOST"
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.parameter import Parameter
    from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
    from geometry_msgs.msg import Point32,PoseStamped
    from nav_msgs.msg import Odometry
    from redline_msgs.action import ExecuteScout
    from redline_msgs.msg import CrewState,MissionState
    from redline_env.scout_flight import ScoutFlightNode
    spec=importlib.util.spec_from_file_location("scout_model",root/"ros_ws/src/redline_description/scripts/generate_scout.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    sdf=ET.Element("sdf",version="1.9");world=ET.SubElement(sdf,"world",name="scout_action_world")
    ET.SubElement(world,"gravity").text="0 0 -3.721"
    physics=ET.SubElement(world,"physics",name="default",type="ignored")
    ET.SubElement(physics,"max_step_size").text=".001";ET.SubElement(physics,"real_time_factor").text="1"
    for filename,name in (("physics","Physics"),("user-commands","UserCommands"),("scene-broadcaster","SceneBroadcaster")):
        ET.SubElement(world,"plugin",filename=f"gz-sim-{filename}-system",name=f"gz::sim::systems::{name}")
    model=ET.SubElement(world,"model",name="SCENARIO_ground");ET.SubElement(model,"static").text="true"
    ET.SubElement(model,"pose").text="0 0 -3581 0 0 0";link=ET.SubElement(model,"link",name="ground")
    collision=ET.SubElement(link,"collision",name="ground");plane=ET.SubElement(ET.SubElement(collision,"geometry"),"plane")
    ET.SubElement(plane,"normal").text="0 0 1";ET.SubElement(plane,"size").text="200 200"
    world.append(ET.fromstring(module.model_sdf(40.,0.,-3580.8)).find("model"))
    world_path=args.out/"world.sdf";ET.ElementTree(sdf).write(world_path,encoding="utf-8",xml_declaration=True)
    log=(args.out/"gazebo.log").open("w")
    process=subprocess.Popen(["gz","sim","-s","-r","-v","2",str(world_path)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    rclpy.init();flight=ScoutFlightNode(parameter_overrides=[Parameter("origin_map_xyz",value=[40.,0.,-3581.]),Parameter("home_ground_z_m",value=-3581.)])
    probe=rclpy.create_node("scout_action_probe")
    qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    phases=probe.create_publisher(MissionState,"/redline/mission/state",qos)
    crew=probe.create_publisher(PoseStamped,"/crew/EV1/pose",10)
    positions=[]
    def odom(m):
        q=m.pose.pose.orientation;v=m.twist.twist.linear
        positions.append({"t":m.header.stamp.sec+m.header.stamp.nanosec*1e-9,
            "physics_s":m.header.stamp.sec+m.header.stamp.nanosec*1e-9,
            "xyz":[m.pose.pose.position.x+40,m.pose.pose.position.y,m.pose.pose.position.z-3581],"frame":m.header.frame_id,
            "quaternion_xyzw":[q.x,q.y,q.z,q.w],"world_velocity_m_s":[v.x,v.y,v.z]})
    probe.create_subscription(Odometry,"/scout_1/odom",odom,10)
    def tick():
        phases.publish(MissionState(phase=MissionState.PRECURSOR))
        c=PoseStamped();c.header.frame_id="map";c.pose.position.z=-3580.;c.pose.orientation.w=1.;crew.publish(c)
    probe.create_timer(.1,tick)
    client=ActionClient(probe,ExecuteScout,"/scout_1/execute_scout")
    executor=MultiThreadedExecutor(num_threads=4)
    for node in (flight,probe):executor.add_node(node)
    def until(predicate,timeout):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            executor.spin_once(timeout_sec=.01)
            if process.poll() is not None:raise RuntimeError("Gazebo exited")
            if predicate():return
        raise TimeoutError("physical action condition timed out")
    report={"schema":"redline.scout.physical-action.v1","created_at_utc":datetime.now(timezone.utc).isoformat(),
        "passed":False,"status":"SCENARIO","partition":os.environ["GZ_PARTITION"],"perception":"ABSENT",
        "scope":"Actual ExecuteScout/Gazebo motor control on isolated flat terrain; no BXW/perception acceptance",
        "pose_setter_used":False,"origin_map_m":[40,0,-3581]}
    try:
        until(lambda:client.server_is_ready() and flight._safe()[0] and len(positions)>5,25)
        goal=ExecuteScout.Goal(request_id="physical-action-test",vehicle_id="scout_1",altitude_m=2.,max_flight_s=60.)
        goal.corridor.points=[Point32(x=40.,y=0.),Point32(x=43.,y=0.),Point32(x=43.,y=3.),Point32(x=40.,y=3.)]
        feedback=[]
        future=client.send_goal_async(goal,feedback_callback=lambda f:feedback.append(f.feedback.phase))
        until(future.done,6);handle=future.result();assert handle.accepted
        future=handle.get_result_async();until(future.done,85);result=future.result()
        p0=positions[0]["xyz"]
        climb=max(p["xyz"][2] for p in positions)-p0[2]
        travel=max(math.hypot(p["xyz"][0]-40,p["xyz"][1]) for p in positions)
        final=positions[-1]["xyz"]
        from analyze_scout_stability import summary
        metrics=summary(positions)
        checks={"ros_action_succeeded":result.status==4,"flight_without_perception_is_partial":result.result.outcome==1,
            "no_invented_science":len(result.result.evidence_ids)==0,"actual_climb_over_1m":climb>1,
            "actual_horizontal_over_2m":travel>2,"landed_near_home":math.dist(final,[40.,0.,-3580.92])<.7,
            "odom_frame_and_origin":all(p["frame"]=="scout_1/odom" for p in positions),
            "actual_tilt_under_18deg":metrics['tilt_deg']['max']<18.,
            "actual_attitude_rate_p95_under_30deg_s":metrics['attitude_rate_deg_s']['p95']<30.,
            "actual_attitude_rate_max_under_75deg_s":metrics['attitude_rate_deg_s']['max']<75.}
        report.update(checks=checks,passed=all(checks.values()),action_status=result.status,outcome=result.result.outcome,
            reason=result.result.reason,climb_m=climb,travel_m=travel,final_map_xyz_m=final,feedback_phases=sorted(set(feedback)),stability_metrics=metrics)
    except Exception as error:report["error"]=repr(error)
    finally:
        flight._command((0,0,0));executor.shutdown();flight.destroy_node();probe.destroy_node();rclpy.try_shutdown()
        process.send_signal(signal.SIGINT)
        try:process.wait(timeout=8)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        log.close()
        (args.out/"odometry.json").write_text(json.dumps(positions)+"\n")
        (args.out/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report));return 0 if report["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
