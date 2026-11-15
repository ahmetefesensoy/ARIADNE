#!/usr/bin/env bash
# Bounded simulation commissioning; uses supplied fresh ASCII build workspace.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_load_runtime
if [[ $# -lt 1 ]]; then
    printf 'Usage: bash scripts/run-t3.sh <built-ASCII-workspace> [--smoke]\n' >&2
    exit 2
fi
t3_ws="$1"
shift
set +u
source "$t3_ws/install/local_setup.bash"
set -u
if [[ -d "$t3_ws/core" ]]; then
    export PYTHONPATH="$t3_ws/core:${PYTHONPATH:-}"
fi
export ROS_DOMAIN_ID=77 GZ_PARTITION=redline
export GZ_SIM_RESOURCE_PATH="$t3_ws/install/redline_description/share/redline_description/models:${GZ_SIM_RESOURCE_PATH:-}"
cd "$REDLINE_ROOT"
mkdir -p "$REDLINE_TEST_RESULTS"
t3_run_dir="$(mktemp -d "$REDLINE_TEST_RESULTS/t3-runtime-XXXXXXXX")"
export REDLINE_T3_RUNTIME_DIR="$t3_run_dir"
exec "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/t3_supervisor.py" --workspace "$t3_ws" --out "$t3_run_dir" "$@"
