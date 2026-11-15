"""Evaluate real launch substitutions/parameters without executing a process.

launch_ros Node._perform_substitutions is used only for inspecting its resolved
arguments. No action.execute(), launch service or lifecycle transition is run.
"""

import importlib.util
from pathlib import Path

import pytest
import yaml
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument
from launch.substitutions import TextSubstitution
from launch.substitutions import SubstitutionFailure
from launch.utilities import perform_substitutions
from launch_ros.actions import Node


PACKAGE = Path(__file__).resolve().parents[1]


@pytest.fixture
def resolved_launch(monkeypatch):
    spec = importlib.util.spec_from_file_location("redline_navigation_launch", PACKAGE / "launch/navigation.launch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Resolve this source package even before it has been installed by colcon.
    monkeypatch.setattr(module, "FindPackageShare", lambda _: TextSubstitution(text=str(PACKAGE)))
    description = module.generate_launch_description()
    context = LaunchContext()
    context.launch_configurations.update({
        "map": "/tmp/redline-test-map.yaml",
        "spawn_x": "123.25", "spawn_y": "-45.5", "spawn_z": "-3600.5", "spawn_yaw": "0.7",
        "use_sim_time": "true", "autostart": "true", "rviz": "false",
        "params_file": str(PACKAGE / "config/nav2.yaml"),
        "ekf_params_file": str(PACKAGE / "config/ekf.yaml"),
    })
    nodes = {}
    for action in description.entities:
        if isinstance(action, Node):
            action._perform_substitutions(context)
            context.extend_locals({"ros_specific_arguments": {
                "name": "__node:=" + action.node_name.rsplit("/", 1)[-1],
                "ns": "__ns:=" + action.expanded_node_namespace,
            }})
            command = [perform_substitutions(context, part) for part in action.cmd]
            nodes[action.node_name.rsplit("/", 1)[-1]] = (action, command)
    return module, description, context, nodes


def loaded_parameters(command):
    result = []
    for index, arg in enumerate(command):
        if arg == "--params-file":
            result.append(yaml.safe_load(Path(command[index + 1]).read_text()))
    return result


def test_manifest_map_and_nonzero_spawn_are_explicit_launch_inputs(resolved_launch):
    _, description, _, nodes = resolved_launch
    required = {
        action.name for action in description.entities
        if isinstance(action, DeclareLaunchArgument) and action.default_value is None
    }
    assert {"map", "spawn_x", "spawn_y", "spawn_z", "spawn_yaw"} <= required
    _, command = nodes["localization_initial_spawn"]
    expected = {"--x": "123.25", "--y": "-45.5", "--z": "-3600.5", "--yaw": "0.7",
                "--frame-id": "map", "--child-frame-id": "rover_1/odom"}
    for flag, value in expected.items():
        assert command[command.index(flag) + 1] == value
    map_params = loaded_parameters(nodes["map_server"][1])
    assert map_params[-1]["/rover_1/map_server"]["ros__parameters"]["yaml_filename"] == "/tmp/redline-test-map.yaml"


def test_command_chain_has_no_controller_or_smoother_bypass(resolved_launch):
    _, _, _, nodes = resolved_launch
    controller = dict(nodes["controller_server"][0].expanded_remapping_rules)
    smoother = dict(nodes["velocity_smoother"][0].expanded_remapping_rules)
    behavior = dict(nodes["behavior_server"][0].expanded_remapping_rules)
    assert controller["cmd_vel"] == behavior["cmd_vel"] == smoother["cmd_vel"] == "cmd_vel_nav"
    assert smoother["cmd_vel_smoothed"] == "cmd_vel_gated"
    assert all("/tf" not in dict(node.expanded_remapping_rules or []) for node, _ in nodes.values())
    assert dict(nodes["ekf_filter_node"][0].expanded_remapping_rules)["odometry/filtered"] == "odom"


def test_parameters_really_match_namespaces_and_lifecycle_owners(resolved_launch):
    module, _, _, nodes = resolved_launch
    for name, (node, command) in nodes.items():
        assert node.node_name == "/rover_1/" + name
        assert Path(command[0]).is_file(), command[0]
    manager = loaded_parameters(nodes["lifecycle_manager_navigation"][1])
    params = manager[0]["rover_1"]["lifecycle_manager_navigation"]["ros__parameters"]
    assert set(params["node_names"]) == set(module.LIFECYCLE_NODES)
    assert set(params["node_names"]) <= nodes.keys()
    overrides = manager[-1]["/rover_1/lifecycle_manager_navigation"]["ros__parameters"]
    assert overrides["autostart"] is True and overrides["use_sim_time"] is True
    # RewrittenYaml must place both top-level nodes and nested costmap params
    # beneath rover_1; otherwise a valid-looking YAML silently uses defaults.
    nav = loaded_parameters(nodes["controller_server"][1])[0]
    assert nav["rover_1"]["controller_server"]["ros__parameters"]["FollowPath"]["vx_max"] == 0.4
    assert nav["rover_1"]["local_costmap"]["local_costmap"]["ros__parameters"]["global_frame"] == "rover_1/odom"
    global_layer = nav["rover_1"]["global_costmap"]["global_costmap"]["ros__parameters"]["obstacle_layer"]
    assert global_layer["min_obstacle_height"] == global_layer["scan"]["min_obstacle_height"] == -3605.5
    assert global_layer["max_obstacle_height"] == global_layer["scan"]["max_obstacle_height"] == -3595.5
    assert nav["rover_1"]["local_costmap"]["local_costmap"]["ros__parameters"]["obstacle_layer"]["scan"]["max_obstacle_height"] == 2.0
    ekf = loaded_parameters(nodes["ekf_filter_node"][1])[0]
    assert ekf["rover_1"]["ekf_filter_node"]["ros__parameters"]["world_frame"] == "rover_1/odom"


def test_installed_custom_bt_is_the_only_default_navigation_tree(resolved_launch):
    _, _, _, nodes = resolved_launch
    files = loaded_parameters(nodes["bt_navigator"][1])
    params = files[-1]["/rover_1/bt_navigator"]["ros__parameters"]
    assert Path(params["default_nav_to_pose_bt_xml"]).resolve() == (PACKAGE / "behavior_trees/navigate_wait_replan.xml").resolve()
    assert Path(params["default_nav_to_pose_bt_xml"]).is_file()
    nav = files[0]["rover_1"]["bt_navigator"]["ros__parameters"]
    assert nav["navigators"] == ["navigate_to_pose"]


@pytest.mark.parametrize("invalid", ["nan", "inf", "-inf", "1.0); print('bad')", ""])
def test_invalid_manifest_coordinates_are_rejected_without_eval(resolved_launch, invalid):
    module, _, context, _ = resolved_launch
    context.launch_configurations["spawn_z"] = invalid
    with pytest.raises(SubstitutionFailure, match="finite number"):
        module.FiniteSpawnCoordinate("spawn_z", offset=5.0).perform(context)
