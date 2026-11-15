#!/usr/bin/env bash
# T5 ROS packages in a fresh isolated ASCII workspace (proje.md §18 T5; D009).
# Builds only the T5 packages and their dependencies; no Gazebo, Unreal or Git.
# Pass package names to test a subset, e.g. `bash scripts/build-t5.sh redline_env`.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_require_python
redline_load_runtime
if [[ ! -x "$REDLINE_VENV/bin/python" ]]; then
    printf 'Run scripts/bootstrap.sh first; T5 node tests use %s\n' "$REDLINE_VENV/bin/python" >&2
    exit 1
fi
packages=("$@")
if [[ ${#packages[@]} -eq 0 ]]; then
    # Every package the T5/T6 launch starts; redline_safety was built but untested before D014.
    packages=(redline_env redline_crew redline_mission redline_safety redline_planner)
fi
mkdir -p "$REDLINE_TEST_RESULTS"
t5_build_dir="$(mktemp -d "$REDLINE_TEST_RESULTS/t5-build-XXXXXXXX")"
t5_workspace="$(env -u PYTHONPATH "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/ros_workspace.py" prepare \
    "$REDLINE_ROOT/ros_ws/src" "$REDLINE_ROS_CACHE" "$t5_build_dir/ros-workspace.json")"
collect() {
    env -u PYTHONPATH "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/ros_workspace.py" collect \
        "$t5_workspace" "$t5_build_dir"
}
trap collect EXIT
cd "$t5_workspace"
colcon build --base-paths "$t5_workspace/src" --packages-up-to "${packages[@]}" \
    --event-handlers console_cohesion+ --cmake-args -DBUILD_TESTING=ON \
    "-DPython3_EXECUTABLE=$REDLINE_SYSTEM_PYTHON" "-DPYTHON_EXECUTABLE=$REDLINE_SYSTEM_PYTHON"
set +u
source "$t5_workspace/install/local_setup.bash"
set -u
colcon test --base-paths "$t5_workspace/src" --packages-select "${packages[@]}" \
    --event-handlers console_cohesion+ --return-code-on-test-failure
colcon test-result --test-result-base "$t5_workspace/build" --verbose
printf 'T5 build evidence: %s\nT5 workspace: %s\n' "$t5_build_dir" "$t5_workspace"
