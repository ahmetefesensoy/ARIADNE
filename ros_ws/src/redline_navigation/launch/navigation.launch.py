"""Single-rover SCENARIO navigation, without a Gazebo pose feedback path.

Python is used for Nav2's namespaced RewrittenYaml and installed BT-path rewrite.
The caller supplies the map and the one-time spawn calibration from its manifest.
RSP, Gazebo, sensor bridges and the physics /clock are owned by bringup.
"""

import math

from launch import LaunchDescription, Substitution
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, SubstitutionFailure
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile, ParameterValue
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml


ROBOT_NAMESPACE = "rover_1"
LIFECYCLE_NODES = (
    "map_server", "planner_server", "controller_server", "behavior_server",
    "velocity_smoother", "collision_monitor", "bt_navigator",
)


class FiniteSpawnCoordinate(Substitution):
    """Resolve numeric manifest coordinates without evaluating user text as code."""

    def __init__(self, name, *, offset=0.0):
        super().__init__()
        self.name = name
        self.offset = offset

    def perform(self, context):
        raw = LaunchConfiguration(self.name).perform(context)
        try:
            value = float(raw)
        except (ValueError, TypeError) as exc:
            raise SubstitutionFailure(f"{self.name} must be a finite number") from exc
        if not math.isfinite(value):
            raise SubstitutionFailure(f"{self.name} must be a finite number")
        return str(value + self.offset)


def generate_launch_description():
    share = FindPackageShare("redline_navigation")
    use_sim_time = LaunchConfiguration("use_sim_time")
    sim_time_parameter = ParameterValue(use_sim_time, value_type=bool)
    nav_params = ParameterFile(
        RewrittenYaml(
            source_file=LaunchConfiguration("params_file"),
            root_key=ROBOT_NAMESPACE,
            param_rewrites={
                "use_sim_time": use_sim_time,
                # Obstacle heights are checked in the costmap global frame.
                # BXW map heights are negative; [0, 2] would discard the scan.
                # This planar T3 filter holds its initial height throughout.
                "global_costmap.global_costmap.ros__parameters.obstacle_layer.min_obstacle_height":
                    FiniteSpawnCoordinate("spawn_z", offset=-5.0),
                "global_costmap.global_costmap.ros__parameters.obstacle_layer.max_obstacle_height":
                    FiniteSpawnCoordinate("spawn_z", offset=5.0),
                "global_costmap.global_costmap.ros__parameters.obstacle_layer.scan.min_obstacle_height":
                    FiniteSpawnCoordinate("spawn_z", offset=-5.0),
                "global_costmap.global_costmap.ros__parameters.obstacle_layer.scan.max_obstacle_height":
                    FiniteSpawnCoordinate("spawn_z", offset=5.0),
            },
            convert_types=True,
        ),
        allow_substs=False,
    )
    ekf_params = ParameterFile(
        RewrittenYaml(
            source_file=LaunchConfiguration("ekf_params_file"),
            root_key=ROBOT_NAMESPACE,
            param_rewrites={"use_sim_time": use_sim_time},
            convert_types=True,
        ),
        allow_substs=False,
    )
    bt_path = PathJoinSubstitution([share, "behavior_trees", "navigate_wait_replan.xml"])

    def nav_node(package, executable, name, *, extra_parameters=None, remappings=None):
        return Node(
            package=package,
            executable=executable,
            name=name,
            namespace=ROBOT_NAMESPACE,
            output="screen",
            parameters=[nav_params] + (extra_parameters or []),
            # TF is deliberately global; frame IDs already carry the rover prefix.
            remappings=remappings or [],
        )

    return LaunchDescription([
        DeclareLaunchArgument("map", description="Absolute DEM-derived ENU occupancy-map YAML"),
        DeclareLaunchArgument("spawn_x", description="Manifest spawn east coordinate (m)"),
        DeclareLaunchArgument("spawn_y", description="Manifest spawn north coordinate (m)"),
        DeclareLaunchArgument("spawn_z", description="Manifest spawn base_link height in map (m)"),
        DeclareLaunchArgument("spawn_yaw", description="Manifest spawn yaw about map +Z (rad)"),
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        DeclareLaunchArgument("autostart", default_value="true"),
        DeclareLaunchArgument("rviz", default_value="false"),
        DeclareLaunchArgument(
            "params_file", default_value=PathJoinSubstitution([share, "config", "nav2.yaml"])),
        DeclareLaunchArgument(
            "ekf_params_file", default_value=PathJoinSubstitution([share, "config", "ekf.yaml"])),
        Node(
            package="tf2_ros", executable="static_transform_publisher",
            name="localization_initial_spawn", namespace=ROBOT_NAMESPACE, output="screen",
            parameters=[{"use_sim_time": sim_time_parameter}],
            arguments=[
                "--x", FiniteSpawnCoordinate("spawn_x"),
                "--y", FiniteSpawnCoordinate("spawn_y"), "--z", FiniteSpawnCoordinate("spawn_z"),
                "--yaw", FiniteSpawnCoordinate("spawn_yaw"), "--pitch", "0.0", "--roll", "0.0",
                "--frame-id", "map", "--child-frame-id", "rover_1/odom",
            ],
        ),
        Node(
            package="robot_localization", executable="ekf_node", name="ekf_filter_node",
            namespace=ROBOT_NAMESPACE, output="screen", parameters=[ekf_params],
            remappings=[("odometry/filtered", "odom")],
        ),
        nav_node("nav2_map_server", "map_server", "map_server", extra_parameters=[{
            "yaml_filename": LaunchConfiguration("map"), "frame_id": "map",
            "topic_name": "map",
        }]),
        nav_node("nav2_planner", "planner_server", "planner_server"),
        nav_node("nav2_controller", "controller_server", "controller_server",
                 remappings=[("cmd_vel", "cmd_vel_nav")]),
        nav_node("nav2_behaviors", "behavior_server", "behavior_server",
                 remappings=[("cmd_vel", "cmd_vel_nav")]),
        nav_node("nav2_velocity_smoother", "velocity_smoother", "velocity_smoother",
                 remappings=[("cmd_vel", "cmd_vel_nav"), ("cmd_vel_smoothed", "cmd_vel_gated")]),
        nav_node("nav2_collision_monitor", "collision_monitor", "collision_monitor"),
        nav_node("nav2_bt_navigator", "bt_navigator", "bt_navigator",
                 extra_parameters=[{"default_nav_to_pose_bt_xml": bt_path}]),
        Node(
            package="nav2_lifecycle_manager", executable="lifecycle_manager",
            name="lifecycle_manager_navigation", namespace=ROBOT_NAMESPACE, output="screen",
            parameters=[nav_params, {
                "use_sim_time": sim_time_parameter,
                "autostart": ParameterValue(LaunchConfiguration("autostart"), value_type=bool),
            }],
        ),
        Node(
            package="rviz2", executable="rviz2", name="rviz_navigation",
            namespace=ROBOT_NAMESPACE, output="screen", condition=IfCondition(LaunchConfiguration("rviz")),
            parameters=[{"use_sim_time": sim_time_parameter}],
            arguments=["-d", PathJoinSubstitution([share, "rviz", "navigation.rviz"])],
            # OGRE1 RViz indexed-map shader fails on this WSL D3D12 renderer;
            # software rendering here is isolated from OGRE2 Gazebo sensors.
            additional_env={"GALLIUM_DRIVER": "llvmpipe"},
        ),
    ])
