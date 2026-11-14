#!/usr/bin/env bash
# Shared paths for WSL/Linux development. Source this file, do not execute it.

REDLINE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
REDLINE_SYSTEM_PYTHON="${REDLINE_SYSTEM_PYTHON:-/usr/bin/python3}"

redline_require_python() {
    "$REDLINE_SYSTEM_PYTHON" -c '
import sys
if sys.version_info[:2] != (3, 12):
    raise SystemExit("REDLINE T0 requires Python 3.12; found " + sys.version.split()[0])
'
}

redline_set_paths() {
    local checkout_key cache_root
    checkout_key="$(printf '%s' "$REDLINE_ROOT" | sha256sum | cut -c 1-16)"
    cache_root="${XDG_CACHE_HOME:-${HOME:?HOME is required}/.cache}"
    REDLINE_VENV="${REDLINE_VENV:-$cache_root/redline/$checkout_key/venv}"
    REDLINE_ROS_CACHE="${REDLINE_ROS_CACHE:-$cache_root/redline/ros}"
    REDLINE_TEST_RESULTS="$REDLINE_ROOT/test-results"
    export REDLINE_ROOT REDLINE_VENV REDLINE_SYSTEM_PYTHON
}

redline_load_runtime() {
    # shellcheck source=../config/runtime.env
    source "$REDLINE_ROOT/config/runtime.env"
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        printf 'Deactivate the active Python virtual environment before ROS builds.\n' >&2
        return 1
    fi
    if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
        printf 'ROS 2 Jazzy underlay not found at /opt/ros/jazzy.\n' >&2
        return 1
    fi
    if [[ -n "${ROS_DISTRO:-}" && "$ROS_DISTRO" != jazzy ]]; then
        printf 'ROS_DISTRO=%s conflicts with the Jazzy target; use a fresh shell.\n' "$ROS_DISTRO" >&2
        return 1
    fi
    # ROS setup scripts legitimately read optional unset variables.
    set +u
    source /opt/ros/jazzy/setup.bash
    set -u
    if [[ "$ROS_DISTRO" != jazzy ]]; then
        printf 'Expected Jazzy after sourcing the underlay.\n' >&2
        return 1
    fi
}

redline_set_paths
