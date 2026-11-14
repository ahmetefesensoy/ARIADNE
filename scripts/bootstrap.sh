#!/usr/bin/env bash
# Install only checkout-local Python development dependencies, without sudo.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

redline_require_python
redline_load_runtime

for required in colcon cmake g++; do
    if ! command -v "$required" >/dev/null; then
        printf 'Required build tool is missing: %s\n' "$required" >&2
        exit 1
    fi
done

if [[ ! -f "$REDLINE_ROOT/python/redline_core/pyproject.toml" ||
      ! -f "$REDLINE_ROOT/python/redline_data/pyproject.toml" ]]; then
    printf 'Both REDLINE Python packages must exist before bootstrap.\n' >&2
    exit 1
fi

# A Linux filesystem cache avoids executable/venv problems on Windows mounts.
# The venv is never under ros_ws/src and is never activated for colcon.
"$REDLINE_SYSTEM_PYTHON" - "$REDLINE_ROOT" "$REDLINE_VENV" <<'PY'
from pathlib import Path
import sys

root, venv = map(lambda value: Path(value).resolve(), sys.argv[1:])
if venv == root or venv.is_relative_to(root):
    raise SystemExit("REDLINE_VENV must be outside the checkout")
if str(venv).startswith("/mnt/"):
    raise SystemExit("REDLINE_VENV must be on a Linux filesystem, not a Windows mount")
PY

if [[ ! -x "$REDLINE_VENV/bin/python" ]]; then
    env -u PYTHONPATH "$REDLINE_SYSTEM_PYTHON" -m venv "$REDLINE_VENV"
fi
env -u PYTHONPATH "$REDLINE_VENV/bin/python" -c '
import sys
if sys.version_info[:2] != (3, 12) or sys.prefix == sys.base_prefix:
    raise SystemExit("Cached environment is not a Python 3.12 venv")
'

env -u PYTHONPATH "$REDLINE_VENV/bin/python" -m pip --disable-pip-version-check install \
    -r "$REDLINE_ROOT/scripts/requirements-test.txt"
env -u PYTHONPATH "$REDLINE_VENV/bin/python" -m pip --disable-pip-version-check install \
    --no-build-isolation \
    -c "$REDLINE_ROOT/scripts/requirements-test.txt" \
    -e "$REDLINE_ROOT/python/redline_core[test]" \
    -e "$REDLINE_ROOT/python/redline_data[test]"

printf '\nPython environment: %s\n' "$REDLINE_VENV"
printf 'Next: bash "%s/scripts/test.sh"\n' "$REDLINE_ROOT"
