#!/usr/bin/env bash
# Fresh isolated ASCII ROS workspace; no T2 Python edits or Git operations.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_require_python
redline_load_runtime
mkdir -p "$REDLINE_TEST_RESULTS"
t3_build_dir="$(mktemp -d "$REDLINE_TEST_RESULTS/t3-build-XXXXXXXX")"
t3_workspace="$(env -u PYTHONPATH "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/ros_workspace.py" prepare \
    "$REDLINE_ROOT/ros_ws/src" "$REDLINE_ROS_CACHE" "$t3_build_dir/ros-workspace.json")"
"$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/snapshot_t3_core.py" "$REDLINE_ROOT" "$t3_workspace"
cp "$t3_workspace/t3-core-inputs.json" "$t3_build_dir/"
export PYTHONPATH="$t3_workspace/core:${PYTHONPATH:-}"
cd "$t3_workspace"
colcon build --base-paths "$t3_workspace/src" --packages-up-to redline_bringup \
    --event-handlers console_cohesion+ --cmake-args -DBUILD_TESTING=ON \
    "-DPython3_EXECUTABLE=$REDLINE_SYSTEM_PYTHON" "-DPYTHON_EXECUTABLE=$REDLINE_SYSTEM_PYTHON"
set +u
source "$t3_workspace/install/local_setup.bash"
set -u
# The live watchdog regression publishes commands. Keep all package tests out
# of the commissioning simulation's domain 77, including concurrent builds.
export ROS_DOMAIN_ID="${REDLINE_T3_TEST_DOMAIN_ID:-78}"
export GZ_PARTITION="redline-t3-tests-$(basename "$t3_build_dir")"
printf '{"ROS_DOMAIN_ID":%s,"GZ_PARTITION":"%s"}\n' "$ROS_DOMAIN_ID" "$GZ_PARTITION" > "$t3_build_dir/test-namespace.json"
colcon test --base-paths "$t3_workspace/src" --packages-select redline_description redline_gazebo redline_navigation redline_bringup \
    --event-handlers console_cohesion+ --return-code-on-test-failure
colcon test-result --test-result-base "$t3_workspace/build" --verbose
env -u PYTHONPATH "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/ros_workspace.py" collect "$t3_workspace" "$t3_build_dir"
printf 'T3 build evidence: %s\nT3 workspace: %s\n' "$t3_build_dir" "$t3_workspace"
