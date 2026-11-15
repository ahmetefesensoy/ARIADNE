# REDLINE rover navigation

This package launches the T3 `rover_1` SCENARIO navigation chain. It was developed
against ROS 2 Jazzy, Nav2 1.3.13 and robot_localization 3.8.3. Bringup supplies the
Gazebo physics clock, sensor bridges, robot_state_publisher and a DEM-derived ENU
occupancy-map YAML. Coordinates and speeds are in metres, radians and seconds.

```bash
ros2 launch redline_navigation navigation.launch.py \
  map:=/absolute/path/to/map.yaml \
  spawn_x:=123.25 spawn_y:=-45.5 spawn_z:=-3600.5 spawn_yaw:=0.7 \
  rviz:=true
```

All five map/spawn arguments are required; the numbers above are an invocation
example, not a BXW spawn prescription. Use the run manifest's actual base_link
pose. Optional arguments are `use_sim_time` (true), `autostart` (true), `rviz`
(false), `params_file` and `ekf_params_file`. The namespace is fixed to `rover_1`.
The map's x/y coordinates must use the same global ENU origin as the spawn.

The EKF consumes `/rover_1/odom_raw` wheel forward/lateral velocity and
`/rover_1/imu` yaw rate. It publishes `/rover_1/odom` and the sole dynamic
`rover_1/odom → rover_1/base_link` TF. It starts at local zero position/yaw.
`localization_initial_spawn` publishes the sole static `map → rover_1/odom`
calibration from the manifest. No ongoing Gazebo world pose is consumed. Do not
bridge a second odometry TF or start AMCL/another map-to-odom broadcaster.

The EKF is planar: roll, pitch and changing height are not estimated. Its map
height remains the supplied initial spawn_z. Global ObstacleLayer height bounds
are rewritten to spawn_z ±5 m, including both layer and observation-source
checks; the local costmap uses odom-relative height. This prevents negative Mars
map elevations from being filtered by a zero-altitude default. A later terrain
localization implementation must replace this initial-height approximation.
Sensor covariance comes from the messages; zero covariance from ideal Gazebo
wheel odometry is not evidence of calibrated localization accuracy.

Smac Hybrid-A* uses forward-only Dubins search and a 4 m SCENARIO turning-radius
preference, matching the search-grid cell size required by Jazzy Smac. Its
analytic expansion is limited to 20 m, five times that radius. MPPI uses
DiffDrive and a 0.4 m/s speed limit. The enclosing footprint
is ±1.0 m by ±0.75 m, based on the scenario rover's chassis/wheels. The global
static map is 4 m; fine obstacle handling uses the 12 m rolling local costmap at
0.2 m and `/rover_1/scan`. A 4 m map cannot resolve subcell terrain hazards.

`InterpolatingPlanner` delegates lifecycle, cancellation and route generation to
Smac Hybrid under the same `GridBased` parameter namespace. It inserts poses at
at most 0.2 m spacing on each returned segment, retaining the original vertices
and endpoint orientations. This fixes an observed two-pose 10 m path on the
coarse grid: MPPI's 3 m path pruning otherwise retained only the current pose.
The adapter does not shortcut bends or increase the map's spatial accuracy.
Inserted orientations use shortest-arc quaternion interpolation. Invalid poses
or an output exceeding 100,000 poses fail rather than allocating without bound.
The same-cell Smac special case is extended to the requested goal using the
actual start orientation. Every output pose is checked against the padded
footprint and map centre; occupied, inscribed and unknown cells reject the
route. Sampling also bounds the outer footprint's rotation travel to 0.2 m.
These checks use the 4 m global map; fine live obstacles still belong to MPPI's
local costmap and collision monitor.
The repaired path uses z=0, consistent with ordinary Smac planar output; negative
Mars map altitude stays in TF/physical terrain, not in a fictitious route ramp.

The sole velocity path is controller `cmd_vel_nav` → closed-loop velocity
smoother `cmd_vel_gated` → collision monitor `cmd_vel`. All are
`geometry_msgs/msg/Twist`. A stale scan or transform stops the monitor's output;
the smoother has a 0.5 s command timeout. The stop/slow polygons are explicit
SCENARIO choices, not measured stopping distances or hardware certification.
Mission command arbitration and `redline_cell_layer` are not implemented here.

The BT replans at 1 Hz and permits three retries separated by a 2 s wait. It has
no Spin, BackUp or automatic costmap clearing. RequestHelp/escalation and
FollowWaypoints are deferred; exhausted navigation returns action failure.
RViz's standard **2D Goal Pose** publishes `/rover_1/goal_pose`, which the
namespaced NavigateToPose navigator consumes. RViz uses the same `/rover_1/map`
and globally shared `/tf`/`/tf_static`; sensor frame IDs carry `rover_1/`.

Offline contract checks, after sourcing Jazzy:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /usr/bin/python3 -m pytest \
  ros_ws/src/redline_navigation/test -q
```

Tests resolve the real launch arguments/parameter YAML without executing nodes,
check installed plugin declarations, command routing, bounded recovery, geometry
and negative-height handling. Full graph operation and goal arrival need a
separate recorded Gazebo/Nav2 run; offline tests do not establish T3 acceptance.

Version-specific references: [MPPI](https://api.nav2.org/nav2-jazzy/html/md_nav2_mppi_controller_README.html),
[Smac Hybrid](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/planners_plugins/smac/smac_hybrid/configuring_smac_hybrid/),
[collision monitor](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/collision_monitor/configuring_collision_monitor_node/),
[velocity smoother](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/configuring_velocity_smoother/),
and [ObstacleLayer source](https://api.nav2.org/nav2-jazzy/html/obstacle__layer_8cpp_source.html).
Configuration and BT were written for this repository; installed Nav2 examples
were inspected to verify API names rather than copied as an application.
