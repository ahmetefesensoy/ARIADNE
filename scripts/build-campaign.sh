#!/usr/bin/env bash
# Combined source snapshot; existing milestone evidence remains historical.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_require_python
redline_load_runtime
evidence="$(mktemp -d "$REDLINE_TEST_RESULTS/campaign-build-XXXXXXXX")"
workspace="$(env -u PYTHONPATH "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/ros_workspace.py" prepare \
    "$REDLINE_ROOT/ros_ws/src" "$REDLINE_ROS_CACHE" "$evidence/ros-workspace.json")"
collect() { env -u PYTHONPATH "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/ros_workspace.py" collect "$workspace" "$evidence"; }
trap collect EXIT
cd "$workspace"
colcon build --base-paths "$workspace/src" --packages-up-to redline_bringup redline_mission redline_planner redline_env redline_crew redline_science \
    --event-handlers console_cohesion+ --cmake-args -DBUILD_TESTING=ON \
    "-DPython3_EXECUTABLE=$REDLINE_SYSTEM_PYTHON" "-DPYTHON_EXECUTABLE=$REDLINE_SYSTEM_PYTHON"
set +u
source "$workspace/install/local_setup.bash"
set -u
export ROS_DOMAIN_ID=160 GZ_PARTITION="redline-campaign-tests-$(basename "$evidence")"
colcon test --base-paths "$workspace/src" --packages-select redline_msgs redline_mission redline_science \
    --event-handlers console_cohesion+ --return-code-on-test-failure
colcon test-result --test-result-base "$workspace/build" --verbose
printf 'Campaign build evidence: %s\nCampaign workspace: %s\n' "$evidence" "$workspace"
