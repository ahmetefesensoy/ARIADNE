#!/usr/bin/env bash
# Optional T1 raster dependencies. Leaves ROS/system Python and core pins alone.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

redline_require_python
if [[ ! -x "$REDLINE_VENV/bin/python" ]]; then
    printf 'Run scripts/bootstrap.sh first. Missing base venv: %s\n' "$REDLINE_VENV" >&2
    exit 1
fi

# Validate the target environment and optional extra before installing anything.
env -u PYTHONPATH "$REDLINE_VENV/bin/python" - \
    "$REDLINE_ROOT/python/redline_data/pyproject.toml" <<'PY'
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys
import tomllib

if sys.version_info[:2] != (3, 12) or sys.prefix == sys.base_prefix:
    raise SystemExit("Data dependencies require the isolated Python 3.12 venv")
metadata = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if "data" not in metadata["project"].get("optional-dependencies", {}):
    raise SystemExit("Declare redline_data[data] before optional data bootstrap")
pins = {
    "numpy": "1.26.4",
    "rasterio": "1.4.3",
    "pyproj": "3.7.1",
    "PyYAML": "6.0.2",
}
for name, expected in pins.items():
    try:
        actual = version(name)
    except PackageNotFoundError:
        continue
    if actual != expected:
        raise SystemExit(
            f"{name} {actual} already installed; refusing to replace it with "
            f"{expected}. Use an explicitly prepared separate REDLINE_VENV."
        )
PY

env -u PYTHONPATH "$REDLINE_VENV/bin/python" -m pip \
    --disable-pip-version-check install --only-binary=:all: \
    -c "$REDLINE_ROOT/scripts/requirements-test.txt" \
    -r "$REDLINE_ROOT/scripts/requirements-data.txt"
env -u PYTHONPATH "$REDLINE_VENV/bin/python" -m pip \
    --disable-pip-version-check install --no-build-isolation --no-deps \
    -e "$REDLINE_ROOT/python/redline_data[data,test]"
env -u PYTHONPATH "$REDLINE_VENV/bin/python" -m pip check

# This is an environment/driver smoke check, not Mars product/CRS validation.
env -u PYTHONPATH "$REDLINE_VENV/bin/python" - <<'PY'
import json
import numpy
import pyproj
import rasterio
import yaml

gdal_version = tuple(int(part) for part in rasterio.__gdal_version__.split(".")[:2])
if gdal_version < (3, 8):
    raise SystemExit(f"GDAL >=3.8 required, found {rasterio.__gdal_version__}")
with rasterio.Env() as environment:
    drivers = environment.drivers()
    missing = {"GTiff", "COG"} - drivers.keys()
    if missing:
        raise SystemExit(f"Required raster drivers missing: {sorted(missing)}")
print(json.dumps({
    "numpy": numpy.__version__,
    "rasterio": rasterio.__version__,
    "gdal_bundled": rasterio.__gdal_version__,
    "pyproj": pyproj.__version__,
    "proj_bundled": pyproj.proj_version_str,
    "PyYAML": yaml.__version__,
    "drivers": ["GTiff", "COG"],
}))
PY

env -u PYTHONPATH "$REDLINE_VENV/bin/redline-data" --version
printf '\nOptional data dependencies ready in %s\n' "$REDLINE_VENV"
printf 'Run bash "%s/scripts/test.sh" to recheck Python and ROS.\n' "$REDLINE_ROOT"
