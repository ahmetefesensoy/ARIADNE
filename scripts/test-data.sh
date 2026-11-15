#!/usr/bin/env bash
# Require the actual GIS runtime: missing optional modules must not become skips.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_require_python
env -u PYTHONPATH "$REDLINE_VENV/bin/python" - <<'PY'
import numpy, rasterio, pyproj, yaml, pytest, jsonschema
print(f"Data test runtime: NumPy {numpy.__version__}, Rasterio {rasterio.__version__}, GDAL {rasterio.__gdal_version__}, PyProj {pyproj.__version__}")
PY
mkdir -p "$REDLINE_TEST_RESULTS"
data_run_dir="$(mktemp -d "$REDLINE_TEST_RESULTS/data-run-XXXXXXXX")"
cd "$REDLINE_ROOT"
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$REDLINE_VENV/bin/python" -m pytest \
    python/redline_core/tests python/redline_data/tests -q --junitxml="$data_run_dir/python.xml"
env -u PYTHONPATH "$REDLINE_VENV/bin/python" - "$data_run_dir/python.xml" <<'PY'
import sys
from xml.etree import ElementTree
root = ElementTree.parse(sys.argv[1]).getroot()
skipped = sum(int(suite.get("skipped", 0)) for suite in root.iter("testsuite"))
if skipped:
    raise SystemExit(f"Data acceptance does not allow skipped tests: {skipped}")
PY
printf 'Data test evidence: %s\n' "$data_run_dir"
