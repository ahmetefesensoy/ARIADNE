"""Human-directed campaign; mutually exclusive with nominal/orientation managers."""
import os
import json
from pathlib import Path
import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    root = Path(LaunchConfiguration("redline_root").perform(context))
    python = LaunchConfiguration("python").perform(context)
    targets = LaunchConfiguration("targets_file").perform(context)
    run_id = LaunchConfiguration("run_id").perform(context)
    scout_mode = LaunchConfiguration("scout_mode").perform(context)
    if not root.is_dir() or not os.access(python, os.X_OK) or not Path(targets).is_file():
        raise ValueError("explicit root, Python and staged terrain targets required")
    grid = str(root/"data/derived/BXW/planning/bxw_planning_4m_v2.npz")
    configs = {name: str(root/"config"/(name.replace("_file", "")+".yaml")) for name in ("crew_file", "suit_file", "eva_file")}
    eva = yaml.safe_load(Path(configs["eva_file"]).read_text())
    nodes = [
        Node(package="redline_science",executable="lab_assay",prefix=python,output="screen",
             parameters=[{"redline_root":str(root),"run_id":run_id}]),
        Node(package="redline_env", executable="sim_clock", prefix=python, output="screen", parameters=[{"running":False,"time_scale":1.}]),
        Node(package="redline_mission", executable="cell_store", prefix=python, output="screen",
             parameters=[{"planning_grid":grid,"suit_file":configs["suit_file"],"site_id":"BXW"}]),
        Node(package="redline_planner", executable="walkback_field", prefix=python, output="screen",
             parameters=[{**configs,"planning_grid":grid,"crew_ids":["EV1"]}]),
        Node(package="redline_crew", executable="ev_sim", name="ev_sim_ev1", prefix=python, output="screen",
             parameters=[{**configs,"crew_id":"EV1","scenario_pose_speed_cap_m_s":3.}]),
        Node(package="redline_mission", executable="campaign_controller", prefix=python, output="screen",
             parameters=[{"redline_root":str(root),"targets_file":targets,"run_id":run_id}]),
        Node(package="redline_mission", executable="campaign_robot_pose", prefix=python, output="screen",
             parameters=[{"use_sim_time":True}]),
        Node(package="redline_science", executable="science_instruments", prefix=python, output="screen",
             parameters=[{"targets_file":targets,"products_dir":str(root/"data/products"),"run_id":run_id,
                          "simulated_backend":True,"physical_mode":False,"auto_activate":True,"operation_duration_s":10.}]),
    ]
    if scout_mode=="physical":
        scout=json.loads(Path(targets).with_name("scout_1.json").read_text())
        nodes.append(Node(package="redline_env",executable="scout_flight",prefix=python,output="screen",
            parameters=[{"planning_grid":grid,"truth_file":str(root/"data/derived/BXW/scenario/scenario_rocks_4.json"),
                "origin_map_xyz":scout["origin_map_xyz_m"],"home_ground_z_m":float(scout["ground_z_m"]),
                "speed_m_s":4.,"survey_spacing_m":20.}]))
    elif scout_mode=="stub":
        nodes.append(Node(package="redline_env",executable="scout_stub",prefix=python,output="screen",
            parameters=[{"planning_grid":grid,"truth_file":str(root/"data/derived/BXW/scenario/scenario_rocks_4.json"),
                "home_xy":[float(v) for v in eva["habitat"]["requested_xy_m"]],"time_scale":30.}]))
    else:raise ValueError("scout_mode must be physical or stub")
    return nodes


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument(name) for name in ("redline_root","python","targets_file","run_id")]
                             +[DeclareLaunchArgument("scout_mode",default_value="stub")]
                             +[OpaqueFunction(function=setup)])
