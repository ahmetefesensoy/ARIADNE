#!/usr/bin/env bash
# Use the already installed Ubuntu Gazebo/Protobuf bindings in this project's venv.
# Only the installed google namespace is exposed, not the whole distro site
# (which would also inject an incompatible coverage package into Numba).
# No third-party package is copied or downloaded.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_load_runtime
test -f /usr/lib/python3/dist-packages/google/protobuf/__init__.py
site="$($REDLINE_VENV/bin/python -c 'import sysconfig;print(sysconfig.get_path("purelib"))')"
case "$site" in "$REDLINE_VENV"/*) ;; *) echo 'venv site path escaped project runtime' >&2;exit 2;; esac
mkdir -p "$site/redline_gazebo_distro"
if [[ ! -e "$site/redline_gazebo_distro/google" ]];then
    ln -s /usr/lib/python3/dist-packages/google "$site/redline_gazebo_distro/google"
fi
printf '%s\n' "$site/redline_gazebo_distro" >"$site/redline_gazebo_distro.pth"
"$REDLINE_VENV/bin/python" -c 'from google.protobuf import __version__;from gz.transport13 import Node;from gz.msgs10.odometry_pb2 import Odometry;import numba;print("Installed distro Protobuf",__version__,"Gazebo Transport and project Numba import successfully")'
