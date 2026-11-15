"""Offline navigation invariants; these tests do not start a ROS process."""

import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml
from ament_index_python.packages import get_package_share_directory


PACKAGE = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def nav():
    return yaml.safe_load((PACKAGE / "config/nav2.yaml").read_text())


def parameters(nav, node):
    return nav[node]["ros__parameters"]


def costmap(nav, name):
    return nav[name][name]["ros__parameters"]


def test_filter_estimates_local_motion_without_global_pose_feedback():
    ekf = yaml.safe_load((PACKAGE / "config/ekf.yaml").read_text())["ekf_filter_node"]["ros__parameters"]
    assert ekf["odom0"] == "/rover_1/odom_raw"
    assert ekf["imu0"] == "/rover_1/imu"
    # No world pose, absolute IMU yaw, gravity/acceleration, or double-counted yaw rate.
    assert len(ekf["odom0_config"]) == len(ekf["imu0_config"]) == 15
    assert {i for i, used in enumerate(ekf["odom0_config"]) if used} == {6, 7}
    assert {i for i, used in enumerate(ekf["imu0_config"]) if used} == {11}
    assert ekf["world_frame"] == ekf["odom_frame"] == "rover_1/odom"
    assert ekf["base_link_frame"] == "rover_1/base_link"
    assert ekf["publish_tf"] and ekf["two_d_mode"] and ekf["use_sim_time"]
    assert not any(key.startswith(("pose", "twist")) or key in {"odom1", "imu1"} for key in ekf)


def test_controller_smoother_and_monitor_have_a_consistent_command_contract(nav):
    controller = parameters(nav, "controller_server")
    mppi = controller["FollowPath"]
    smoother = parameters(nav, "velocity_smoother")
    monitor = parameters(nav, "collision_monitor")
    assert mppi["motion_model"] == "DiffDrive"
    assert mppi["model_dt"] == pytest.approx(1.0 / controller["controller_frequency"])
    assert 0 < mppi["vx_max"] <= 0.4
    assert smoother["max_velocity"][0] == mppi["vx_max"]
    assert smoother["max_velocity"][2] == mppi["wz_max"]
    assert smoother["max_accel"][0] == mppi["ax_max"]
    assert smoother["max_decel"][0] == mppi["ax_min"]
    assert mppi["vx_min"] == smoother["min_velocity"][0] == 0.0
    assert mppi["vy_max"] == smoother["max_velocity"][1] == 0.0
    assert monitor["cmd_vel_in_topic"] == "cmd_vel_gated"
    assert monitor["cmd_vel_out_topic"] == "cmd_vel"
    assert all(parameters(nav, name)["enable_stamped_cmd_vel"] is False for name in (
        "controller_server", "behavior_server", "velocity_smoother", "collision_monitor"))
    assert controller["odom_topic"] == smoother["odom_topic"] == "/rover_1/odom"
    assert 0 < smoother["velocity_timeout"] <= 0.5
    assert 0 < monitor["source_timeout"] <= 0.5
    assert monitor["scan"]["source_timeout"] > 0  # Never disable missing-sensor stop.


def test_costmaps_share_global_map_and_prefixed_sensor_frames(nav):
    global_map = costmap(nav, "global_costmap")
    local_map = costmap(nav, "local_costmap")
    assert global_map["global_frame"] == "map"
    assert local_map["global_frame"] == "rover_1/odom"
    assert global_map["static_layer"]["map_topic"] == "/rover_1/map"
    assert global_map["static_layer"]["map_subscribe_transient_local"]
    assert global_map["static_layer"]["trinary_costmap"] is False
    assert "static_layer" not in local_map["plugins"]  # Avoid resizing fine rolling grid to 4 m.
    assert local_map["rolling_window"] and local_map["resolution"] <= 0.2
    for grid in (global_map, local_map):
        assert grid["robot_base_frame"] == "rover_1/base_link"
        scan = grid["obstacle_layer"]["scan"]
        assert scan["topic"] == "/rover_1/scan"
        assert scan["data_type"] == "LaserScan" and scan["marking"] and scan["clearing"]
        assert scan["raytrace_max_range"] >= scan["obstacle_max_range"] > 0
    planner = parameters(nav, "planner_server")["GridBased"]
    assert planner["plugin"] == "redline_navigation::InterpolatingPlanner"
    assert planner["delegate_plugin"] == "nav2_smac_planner::SmacPlannerHybrid"
    assert 0 < planner["densification_step"] <= 0.2
    assert not planner["allow_unknown"]
    assert planner["minimum_turning_radius"] >= global_map["resolution"]
    assert planner["analytic_expansion_max_length"] >= 4 * planner["minimum_turning_radius"]


def test_collision_zones_enclose_padded_robot_footprint(nav):
    # Detect a geometry edit that leaves a wheel outside the protective zone.
    local_map = costmap(nav, "local_costmap")
    assert local_map["footprint"] == costmap(nav, "global_costmap")["footprint"]
    footprint = json.loads(local_map["footprint"])
    padding = local_map["footprint_padding"]
    monitor = parameters(nav, "collision_monitor")
    stop = json.loads(monitor["Stop"]["points"])
    slow = json.loads(monitor["Slow"]["points"])
    for axis, actual_half_extent in ((0, 0.98), (1, 0.715)):
        footprint_extent = max(abs(point[axis]) for point in footprint)
        stop_extent = max(abs(point[axis]) for point in stop)
        slow_extent = max(abs(point[axis]) for point in slow)
        assert actual_half_extent <= footprint_extent
        assert footprint_extent + padding < stop_extent < slow_extent
    assert monitor["Stop"]["action_type"] == "stop"
    assert monitor["Stop"]["min_points"] >= 1
    assert monitor["Slow"]["action_type"] == "limit"
    assert monitor["Slow"]["linear_limit"]==pytest.approx(parameters(nav,"velocity_smoother")["max_velocity"][0]*.3)
    assert monitor["Slow"]["angular_limit"]==pytest.approx(parameters(nav,"velocity_smoother")["max_velocity"][2]*.3)
    assert monitor["observation_sources"] == ["scan"]
    assert monitor["scan"]["topic"] == "/rover_1/scan" and monitor["scan"]["enabled"]
    # Prediction horizon must fit inside the rolling grid, including robot body.
    mppi = parameters(nav, "controller_server")["FollowPath"]
    distance = mppi["time_steps"] * mppi["model_dt"] * mppi["vx_max"]
    assert distance + max(abs(p[0]) for p in footprint) < local_map["width"] / 2


def test_behavior_tree_retries_are_bounded_and_cannot_invoke_motion_recovery(nav):
    root = ET.parse(PACKAGE / "behavior_trees/navigate_wait_replan.xml").getroot()
    assert root.attrib["BTCPP_format"] == "4"
    allowed = {"root", "BehaviorTree", "RecoveryNode", "PipelineSequence", "RateController",
               "ComputePathToPose", "FollowPath", "ReactiveFallback", "GoalUpdated", "Wait"}
    assert {node.tag for node in root.iter()} <= allowed
    recovery = root.find(".//RecoveryNode")
    assert 0 < int(recovery.attrib["number_of_retries"]) <= 3
    assert float(root.find(".//RateController").attrib["hz"]) == 1.0
    assert 0 < float(root.find(".//Wait").attrib["wait_duration"]) <= 2.0
    assert root.find(".//ComputePathToPose").attrib["planner_id"] in parameters(nav, "planner_server")["planner_plugins"]
    assert root.find(".//FollowPath").attrib["controller_id"] in parameters(nav, "controller_server")["controller_plugins"]
    behavior = parameters(nav, "behavior_server")
    assert behavior["behavior_plugins"] == ["wait"]
    assert parameters(nav, "bt_navigator")["navigators"] == ["navigate_to_pose"]


def test_all_navigation_nodes_use_physics_sim_time(nav):
    for name, value in nav.items():
        params = costmap(nav, name) if name in {"global_costmap", "local_costmap"} else value["ros__parameters"]
        assert params["use_sim_time"] is True, name


@pytest.mark.parametrize("package,plugin", [
    ("nav2_rotation_shim_controller", "nav2_rotation_shim_controller::RotationShimController"),
    ("nav2_regulated_pure_pursuit_controller", "nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController"),
    ("nav2_controller", "nav2_controller::PoseProgressChecker"),
    ("redline_navigation", "redline_navigation::InterpolatingPlanner"),
    ("nav2_smac_planner", "nav2_smac_planner::SmacPlannerHybrid"),
    ("nav2_mppi_controller", "nav2_mppi_controller::MPPIController"),
    ("nav2_controller", "nav2_controller::SimpleGoalChecker"),
    ("nav2_controller", "nav2_controller::SimpleProgressChecker"),
    ("nav2_behaviors", "nav2_behaviors::Wait"),
    ("nav2_bt_navigator", "nav2_bt_navigator::NavigateToPoseNavigator"),
])
def test_selected_plugins_exist_in_the_installed_ros_distribution(package, plugin):
    share = Path(get_package_share_directory(package))
    declared = {
        node.attrib.get("type")
        for path in share.glob("*.xml")
        for node in ET.parse(path).getroot().iter("class")
    }
    assert plugin in declared, f"Plugin absent from installed {package}: {plugin}"


def test_rviz_goal_and_map_topics_match_the_namespaced_nav2_interfaces():
    rviz = yaml.safe_load((PACKAGE / "rviz/navigation.rviz").read_text())["Visualization Manager"]
    assert rviz["Global Options"]["Fixed Frame"] == "map"
    goal_tools = [tool for tool in rviz["Tools"] if tool["Class"] == "rviz_default_plugins/SetGoal"]
    assert len(goal_tools) == 1
    assert goal_tools[0]["Topic"]["Value"] == "/rover_1/goal_pose"
    map_display = next(display for display in rviz["Displays"] if display["Class"] == "rviz_default_plugins/Map")
    assert map_display["Topic"]["Value"] == "/rover_1/map"
    assert map_display["Topic"]["Durability Policy"] == "Transient Local"
    for display in rviz['Displays']:
        topic=display.get('Topic',{})
        if topic.get('Value') in ('/rover_1/collision_stop','/rover_1/collision_slow'):
            assert topic['Durability Policy']=='Volatile'  # Nav2 polygon publisher uses system-default QoS.
