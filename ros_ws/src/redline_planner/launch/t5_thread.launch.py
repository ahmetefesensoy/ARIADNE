"""T5 steel thread without Gazebo (proje.md §18.1, §18 T5; D009).

sim_clock (PET) → ev_sim (crew posed by Unreal) → cell_store → walkback_field →
MarginField / RedLine / FieldTile, optionally with rosbridge on 127.0.0.1:9090
for Unreal. Nodes import redline_core (numba, scipy, scikit-image), so they run
under the REDLINE venv Python (``python``, default $REDLINE_PYTHON or
$REDLINE_VENV/bin/python). Default inputs are the repo's BXW planning grid and
SCENARIO configs under ``redline_root`` (default $REDLINE_ROOT).
"""
import os
import json
from datetime import datetime, timezone

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

DEFAULTS = {
    "planning_grid": "data/derived/BXW/planning/bxw_planning_4m_v2.npz",
    "crew_file": "config/crew.yaml",
    "suit_file": "config/suit.yaml",
    "eva_file": "config/eva.yaml",
    "science_file": "config/science_BXW.yaml",
    "targets_file": "data/derived/BXW/planning/targets_v1.json",
}


def _default_python() -> str:
    if os.environ.get("REDLINE_PYTHON"):
        return os.environ["REDLINE_PYTHON"]
    venv = os.environ.get("REDLINE_VENV")
    return os.path.join(venv, "bin", "python") if venv else ""


def _setup(context):
    value = {name: LaunchConfiguration(name).perform(context) for name in
             ("redline_root", "python", "time_scale", "pose_crew_ids", "rosbridge", "rosbridge_port",
              "use_sim_time", "planner", "scenario_file", "env_dir", "rules_file", "sep_shelter_max_min", "sun_table", "intro", "scenario_pose_speed_cap_m_s",
              *DEFAULTS)}
    root = value["redline_root"]
    with_planner = value["planner"].lower() in ("1", "true", "yes")
    intro_enabled = value["intro"].lower() in ("1", "true", "yes")
    if intro_enabled and value["scenario_file"]:
        raise RuntimeError("Orientation walkthrough and S1 replay are separate runs; do not start two mission clocks")
    paths = {}
    for name, relative in DEFAULTS.items():
        paths[name] = value[name] or (os.path.join(root, relative) if root else "")
        needed = with_planner or name not in ("science_file", "targets_file")
        if needed and (not paths[name] or not os.path.exists(paths[name])):
            raise RuntimeError(f"{name} not found ({paths[name]!r}); set redline_root or {name}")
    python = value["python"]
    if not python or not os.access(python, os.X_OK):
        raise RuntimeError("the REDLINE venv Python is required (python:=..., REDLINE_PYTHON or REDLINE_VENV)")
    with open(paths["eva_file"], encoding="utf-8") as handle:
        eva = yaml.safe_load(handle)
    pose_crew = [c for c in value["pose_crew_ids"].split(",") if c]
    sim_time = value["use_sim_time"].lower() in ("1", "true", "yes")
    common = {"use_sim_time": sim_time}
    configs = {"crew_file": paths["crew_file"], "suit_file": paths["suit_file"], "eva_file": paths["eva_file"]}
    scenario = None
    clock = {"time_scale": float(value["time_scale"])}
    if intro_enabled:
        clock["running"] = False
    if value["scenario_file"]:
        with open(value["scenario_file"], encoding="utf-8") as handle:
            scenario = yaml.safe_load(handle)
        # The scenario owns mission time: its scale and start PET (proje.md §16).
        clock = {"time_scale": float(scenario.get("time_scale", 1.0)),
                 "start_pet_s": 60.0 * float(scenario["start"].get("pet_min", 0.0)),
                 "running": False}  # scenario_player starts mission time once the graph is ready
    # D015: one crew list for every node — the scenario's, else eva.yaml's.
    crew_ids = list((scenario or {}).get("crew") or eva["crew_ids"])
    # D015: a scenario that starts before TRAVERSE runs the nominal flow headless: planner_server
    # makes plan v1, mission_manager starts mission time, every crew member walks the plan.
    nominal = scenario is not None and str(scenario.get("initial_phase", "TRAVERSE")) != "TRAVERSE"
    if nominal and not with_planner:
        raise RuntimeError("a nominal-flow scenario (initial_phase before TRAVERSE) needs planner:=true")
    egress_pet_s = 60.0 * float(scenario["start"].get("pet_min", 0.0)) if scenario is not None else 0.0
    # D015 (T7): a robot precursor before egress — voi_tasker proposes, the SIMULATED scout flies.
    precursor = dict((scenario or {}).get("precursor") or {})
    if precursor and not nominal:
        raise RuntimeError("a precursor needs the nominal flow (initial_phase BRIEFING)")
    truth_file = str((scenario or {}).get("truth_file") or "")
    if precursor:
        truth_file = truth_file if os.path.isabs(truth_file) else os.path.join(root, truth_file)
        if not os.path.exists(truth_file):
            raise RuntimeError(f"precursor scenario truth_file not found: {truth_file!r}")
    unknown = sorted(set(pose_crew) - set(crew_ids))
    if unknown:
        raise RuntimeError(f"pose_crew_ids {unknown} are not in the crew list {crew_ids}")
    rules = value["rules_file"] or os.path.join(root, "config", "rules.yaml")
    shelter = {}
    if scenario is not None:
        # FR-12's dusk limit and shelter radius are defined once, in the rules file (D014).
        with open(rules, encoding="utf-8") as handle:
            fr12 = yaml.safe_load(handle)["rules"].get("FR-12", {})
        shelter = {"dusk_min": float(fr12.get("t_dusk_min", 30.0)),
                   "arrive_radius_m": float(fr12.get("shelter_radius_m", 10.0))}
    sun_table = value["sun_table"] if scenario is not None else ""
    actions = [
        Node(package="redline_env", executable="sim_clock", name="sim_clock", prefix=python, output="screen",
             parameters=[{**common, **clock}]),
        Node(package="redline_mission", executable="cell_store", name="cell_store", prefix=python, output="screen",
             parameters=[{**common, "planning_grid": paths["planning_grid"], "suit_file": paths["suit_file"],
                          "site_id": eva["site_id"]}]),
        Node(package="redline_planner", executable="walkback_field", name="walkback_field", prefix=python,
             output="screen", parameters=[{**common, **configs, "planning_grid": paths["planning_grid"],
                                           "sep_shelter_max_min": float(value["sep_shelter_max_min"]),
                                           "sun_table": sun_table, "scenario_file": value["scenario_file"],
                                           "crew_ids": crew_ids, **shelter}]),
    ]
    if intro_enabled:
        with open(os.path.join(root, "data/engines/BXW/eva-runtime-v1.json"), encoding="utf-8") as handle:
            intro = json.load(handle)["intro"]
        actions.append(Node(package="redline_mission", executable="mission_manager", name="mission_manager", prefix=python,
            output="screen", parameters=[{**common, "crew_ids": list(eva["crew_ids"]), "initial_phase": "BRIEFING",
                "intro_enabled": True, "intro_briefing_xy": intro["briefing_xy_m"], "intro_station_xy": intro["station_xy_m"],
                "scenario_id": "BXW_ORIENTATION", "run_id": f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-BXW_ORIENTATION-0"}]))
    if scenario is not None:
        env_dir = value["env_dir"] or os.path.join(root, "data", "env")
        run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{scenario['id']}-{scenario['seed']}"
        actions += [
            Node(package="redline_env", executable="rad_replay", name="rad_replay", prefix=python, output="screen",
                 parameters=[{**common, "scenario_file": value["scenario_file"], "env_dir": env_dir}]),
            Node(package="redline_mission", executable="mission_manager", name="mission_manager", prefix=python,
                 output="screen", parameters=[{**common, "crew_ids": crew_ids,
                                               "run_id": run_id, "scenario_id": scenario["id"],
                                               "initial_phase": str(scenario.get("initial_phase", "TRAVERSE")),
                                               "nominal_flow": nominal, "site_id": eva["site_id"],
                                               "precursor": bool(precursor),
                                               "precursor_vehicle": str(precursor.get("vehicle_id", "scout_1")),
                                               "egress_pet_s": egress_pet_s,
                                               "plan_objective": str((scenario.get("plan") or {}).get(
                                                   "objective", "SCIENCE")),
                                               "plan_max_duration_min": float((scenario.get("plan") or {}).get(
                                                   "max_duration_min", 300.0)),
                                               "plan_target_ids": list((scenario.get("plan") or {}).get(
                                                   "target_ids") or [""])}]),
            Node(package="redline_safety", executable="rule_monitor", name="rule_monitor", prefix=python,
                 output="screen", parameters=[{**common, "rules_file": rules, "crew_ids": crew_ids,
                                               "planning_grid": paths["planning_grid"],
                                               "suit_file": paths["suit_file"], "eva_file": paths["eva_file"],
                                               "sun_table": sun_table, "scenario_file": value["scenario_file"]}]),
        ]
        if sun_table:
            actions.append(Node(package="redline_env", executable="env_server", name="env_server", prefix=python,
                                output="screen", parameters=[{**common, "sun_table": sun_table,
                                                              "scenario_file": value["scenario_file"]}]))
        actions += [
            Node(package="redline_env", executable="scenario_player", name="scenario_player", prefix=python,
                 output="screen", parameters=[{**common, "scenario_file": value["scenario_file"],
                                               "run_id": run_id,
                                               # nominal flow: mission_manager starts time at egress
                                               "auto_start": not nominal}]),
        ]
    if with_planner:
        actions.append(Node(package="redline_planner", executable="planner_server", name="planner_server",
                            prefix=python, output="screen",
                            parameters=[{**common, **configs, "planning_grid": paths["planning_grid"],
                                         "science_file": paths["science_file"],
                                         "targets_file": paths["targets_file"], "crew_ids": crew_ids}]))
    if precursor:
        # Only the SIMULATED observer gets the hidden truth (D015 isolation).
        actions += [
            Node(package="redline_mission", executable="voi_tasker", name="voi_tasker", prefix=python, output="screen",
                 parameters=[{**common, **configs, "planning_grid": paths["planning_grid"],
                              "science_file": paths["science_file"], "targets_file": paths["targets_file"],
                              "voi_file": os.path.join(root, "config", "voi.yaml"), "crew_ids": crew_ids,
                              "vehicle_id": str(precursor.get("vehicle_id", "scout_1"))}]),
            Node(package="redline_env", executable="scout_stub", name="scout_stub", prefix=python, output="screen",
                 parameters=[{**common, "truth_file": truth_file, "planning_grid": paths["planning_grid"],
                              "vehicle_id": str(precursor.get("vehicle_id", "scout_1")),
                              "home_xy": [float(v) for v in eva["habitat"]["requested_xy_m"]],
                              "time_scale": float(scenario.get("time_scale", 1.0))}]),
        ]
    if nominal:  # SIMULATED walk along the plan for every crew member (D015)
        trail = scenario.get("crew_trail_s") or {}
        actions += [
            Node(package="redline_crew", executable="ev_sim", name=f"ev_sim_{crew_id.lower()}", prefix=python,
                 output="screen", parameters=[{**common, **configs, "crew_id": crew_id, "motion": "plan",
                                               "planning_grid": paths["planning_grid"],
                                               "trail_s": float(trail.get(crew_id, 0.0)),
                                               "egress_pet_s": egress_pet_s}])
            for crew_id in crew_ids
        ]
    else:
        actions += [
            Node(package="redline_crew", executable="ev_sim", name=f"ev_sim_{crew_id.lower()}", prefix=python,
                 output="screen", parameters=[{**common, **configs, "crew_id": crew_id,
                    "scenario_pose_speed_cap_m_s": float(value["scenario_pose_speed_cap_m_s"])}])
            for crew_id in pose_crew
        ]
    if value["rosbridge"].lower() in ("1", "true", "yes"):
        rosbridge = os.path.join(get_package_share_directory("rosbridge_server"), "launch",
                                 "rosbridge_websocket_launch.xml")
        actions.append(IncludeLaunchDescription(AnyLaunchDescriptionSource(rosbridge), launch_arguments={
            "port": value["rosbridge_port"], "address": "127.0.0.1"}.items()))
    return actions


def generate_launch_description():
    arguments = [
        DeclareLaunchArgument("redline_root", default_value=os.environ.get("REDLINE_ROOT", "")),
        DeclareLaunchArgument("python", default_value=_default_python()),
        DeclareLaunchArgument("time_scale", default_value="1.0", description="PET seconds per wall second"),
        DeclareLaunchArgument("pose_crew_ids", default_value="EV1",
                              description="comma-separated crew posed from Unreal (/crew/<id>/pose)"),
        DeclareLaunchArgument("rosbridge", default_value="false"),
        DeclareLaunchArgument("rosbridge_port", default_value="9090"),
        DeclareLaunchArgument("planner", default_value="true", description="start planner_server (PlanEva)"),
        DeclareLaunchArgument("intro", default_value="false", description="SCENARIO orientation walkthrough; starts PET paused"),
        DeclareLaunchArgument("scenario_pose_speed_cap_m_s", default_value="0.0", description="Explicit interactive SCENARIO sprint metering; 0 retains walking-only cap"),
        DeclareLaunchArgument("scenario_file", default_value="",
                              description="config/scenarios/*.yaml: adds rad_replay, mission_manager, rule_monitor"),
        DeclareLaunchArgument("env_dir", default_value="", description="RAD tables (default <root>/data/env)"),
        DeclareLaunchArgument("rules_file", default_value="", description="default <root>/config/rules.yaml"),
        DeclareLaunchArgument("sep_shelter_max_min", default_value="20.0", description="FR-03 T_SEP_max"),
        DeclareLaunchArgument("sun_table", default_value="",
                              description="SPICE sun table CSV: env_server and the FR-12 daylight term"),
        DeclareLaunchArgument("use_sim_time", default_value="false",
                              description="the thread needs no Gazebo; true only with a running /clock"),
    ] + [DeclareLaunchArgument(name, default_value="") for name in DEFAULTS]
    return LaunchDescription(arguments + [OpaqueFunction(function=_setup)])
