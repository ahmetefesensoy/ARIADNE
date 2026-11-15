#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_load_runtime
set +u
source "${1:?workspace required}/install/local_setup.bash"
set -u
export ROS_DOMAIN_ID=168 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPATH="$REDLINE_ROOT/ros_ws/src/redline_science:$PYTHONPATH"
exec "$REDLINE_VENV/bin/python" -m pytest "$REDLINE_ROOT/ros_ws/src/redline_science/test/test_lab_assay.py" -q --junitxml="$REDLINE_TEST_RESULTS/lab-dds-fixed.xml"
