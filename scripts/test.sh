#!/usr/bin/env bash
# Run the same pure-Python and ROS-interface checks locally and in CI.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

redline_require_python
redline_load_runtime
if [[ ! -x "$REDLINE_VENV/bin/python" ]]; then
    printf 'Run scripts/bootstrap.sh before tests. Missing venv: %s\n' "$REDLINE_VENV" >&2
    exit 1
fi

# Reports use a fresh run directory so an interrupted build cannot expose old
# successful XML files as evidence for the current run.
mkdir -p -- "$REDLINE_TEST_RESULTS"
REDLINE_RUN_RESULTS="$(mktemp -d "$REDLINE_TEST_RESULTS/run-XXXXXXXX")"
cd -- "$REDLINE_ROOT"
# ROS underlay PYTHONPATH and its pytest entry points must not leak into the
# ROS-independent package tests. Colcon below keeps the full ROS environment.
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    "$REDLINE_VENV/bin/python" -m pytest \
    python/redline_core/tests python/redline_data/tests \
    --junitxml="$REDLINE_RUN_RESULTS/python.xml"

REDLINE_ROS_WORKSPACE="$(env -u PYTHONPATH "$REDLINE_SYSTEM_PYTHON" \
    "$REDLINE_ROOT/scripts/ros_workspace.py" prepare \
    "$REDLINE_ROOT/ros_ws/src" "$REDLINE_ROS_CACHE" \
    "$REDLINE_RUN_RESULTS/ros-workspace.json")"

collect_ros_reports() {
    env -u PYTHONPATH "$REDLINE_SYSTEM_PYTHON" \
        "$REDLINE_ROOT/scripts/ros_workspace.py" collect \
        "$REDLINE_ROS_WORKSPACE" "$REDLINE_RUN_RESULTS"
}
trap collect_ros_reports EXIT

cd -- "$REDLINE_ROS_WORKSPACE"
# The exact source snapshot has an ASCII path for rosidl/CMake. Only application
# packages are discovered and the fresh workspace cannot contain stale overlays.
# ROS generation uses distro Python, never the pure-Python test environment.
colcon build \
    --base-paths "$REDLINE_ROS_WORKSPACE/src" \
    --event-handlers console_cohesion+ \
    --cmake-args \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DBUILD_TESTING=ON \
        "-DPython3_EXECUTABLE=$REDLINE_SYSTEM_PYTHON" \
        "-DPYTHON_EXECUTABLE=$REDLINE_SYSTEM_PYTHON"

set +u
source "$REDLINE_ROS_WORKSPACE/install/local_setup.bash"
set -u
colcon test \
    --base-paths "$REDLINE_ROS_WORKSPACE/src" \
    --event-handlers console_cohesion+ \
    --return-code-on-test-failure
colcon test-result --test-result-base "$REDLINE_ROS_WORKSPACE/build" --verbose
printf '\nReports: %s\nROS workspace: %s\n' "$REDLINE_RUN_RESULTS" "$REDLINE_ROS_WORKSPACE"
