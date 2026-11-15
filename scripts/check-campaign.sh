#!/usr/bin/env bash
# Extra source tests during integration; receipts explicitly name the source scope.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_load_runtime
set +u
source "${1:?workspace required}/install/local_setup.bash"
set -u
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=161 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export PYTHONPATH="$REDLINE_ROOT/ros_ws/src/redline_mission:$PYTHONPATH"
"$REDLINE_VENV/bin/python" -m pytest "$REDLINE_ROOT/ros_ws/src/redline_mission/test/test_campaign_robot_pose.py" -q \
    --junitxml="$REDLINE_TEST_RESULTS/campaign-robot-pose-dds.xml"
export ROS_DOMAIN_ID=162 PYTHONPATH="$REDLINE_ROOT/ros_ws/src/redline_env:$PYTHONPATH"
"$REDLINE_VENV/bin/python" -m pytest "$REDLINE_ROOT/ros_ws/src/redline_env/test/test_scout_flight.py" -q \
    --junitxml="$REDLINE_TEST_RESULTS/scout-flight-gates.xml"
