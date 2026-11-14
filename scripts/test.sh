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

mkdir -p -- "$REDLINE_TEST_RESULTS"
cd -- "$REDLINE_ROOT"
# ROS underlay PYTHONPATH and its pytest entry points must not leak into the
# ROS-independent package tests. Colcon below keeps the full ROS environment.
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    "$REDLINE_VENV/bin/python" -m pytest \
    python/redline_core/tests python/redline_data/tests \
    --junitxml="$REDLINE_TEST_RESULTS/python.xml"

cd -- "$REDLINE_ROOT/ros_ws"
# Only application packages are discovered; archived skill/helper packages are
# deliberately outside this base path. ROS generation uses the distro Python,
# not the isolated pure-Python test environment.
colcon build \
    --base-paths "$REDLINE_ROOT/ros_ws/src" \
    --event-handlers console_cohesion+ \
    --cmake-args \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DBUILD_TESTING=ON \
        "-DPython3_EXECUTABLE=$REDLINE_SYSTEM_PYTHON" \
        "-DPYTHON_EXECUTABLE=$REDLINE_SYSTEM_PYTHON"

set +u
source "$REDLINE_ROOT/ros_ws/install/local_setup.bash"
set -u
colcon test \
    --base-paths "$REDLINE_ROOT/ros_ws/src" \
    --event-handlers console_cohesion+ \
    --return-code-on-test-failure
colcon test-result --test-result-base "$REDLINE_ROOT/ros_ws/build" --verbose
