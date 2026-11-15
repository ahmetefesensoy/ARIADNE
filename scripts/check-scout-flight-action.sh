#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_load_runtime
set +u
source "${1:?workspace required}/install/local_setup.bash"
set -u
export PYTHONPATH="$REDLINE_ROOT/ros_ws/src/redline_env:$PYTHONPATH"
exec "$REDLINE_VENV/bin/python" "$REDLINE_ROOT/scripts/verify_scout_flight_action.py" --out "$REDLINE_TEST_RESULTS/scout-physical-action"
