#!/usr/bin/env bash
# Start only rosbridge against an explicitly selected, already-built workspace.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
if [[ $# -lt 1 || "$1" == --help ]]; then
    printf 'Usage: bash scripts/t4_rosbridge.sh <built-workspace> [name:=value ...]\n'
    printf 'T4_ROSBRIDGE_PORT=9090 T4_ROSBRIDGE_ADDRESS=127.0.0.1\n'
    exit 0
fi
t4_workspace="$(realpath -- "$1")"
shift
if [[ ! -f "$t4_workspace/install/local_setup.bash" ]]; then
    printf 'Workspace has no install/local_setup.bash: %s\n' "$t4_workspace" >&2
    exit 2
fi
redline_load_runtime
set +u
source "$t4_workspace/install/local_setup.bash"
set -u
ros2 pkg prefix rosbridge_server >&2
printf 'rosbridge workspace=%s domain=%s address=%s port=%s\n' \
    "$t4_workspace" "$ROS_DOMAIN_ID" "${T4_ROSBRIDGE_ADDRESS:-127.0.0.1}" \
    "${T4_ROSBRIDGE_PORT:-9090}" >&2
exec "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/t4_bridge_runtime.py" "$@"
