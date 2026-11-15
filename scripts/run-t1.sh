#!/usr/bin/env bash
# Reproduce the BXW T1 chain using pinned source evidence and local hash caches.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_require_python
cd "$REDLINE_ROOT"
mkdir -p "$REDLINE_TEST_RESULTS"
t1_log_dir="$(mktemp -d "$REDLINE_TEST_RESULTS/t1-run-XXXXXXXX")"
t1_run_key="$(basename "$t1_log_dir")"
t1_metadata_dir="$REDLINE_ROOT/data/stac/BXW/$t1_run_key"
mkdir -p "$t1_metadata_dir"
cli() {
    local stage="$1"
    shift
    printf 'T1: %s\n' "$stage"
    env -u PYTHONPATH "$REDLINE_VENV/bin/redline-data" "$@" > "$t1_log_dir/$stage.json"
}
for evidence_file in docs/verification/T1_VERTICAL_DATUM.json docs/verification/T1_HIRISE_TRANSFER.json; do
    if [[ ! -f "$evidence_file" ]]; then
        printf 'Missing pinned product evidence: %s\n' "$evidence_file" >&2
        exit 1
    fi
done
cli catalog catalog --site BXW --product gale_dem_v3 --product hirise_dtm_bxw_019698 --out "$t1_metadata_dir/catalog.json"
for product in gale_dem_v3 hirise_dtm_bxw_019698; do
    cli "fetch-$product" fetch --site BXW --product "$product" --expected-radius-m 3396190 --out "data/raw/BXW/$product.tif"
    cli "crs-$product" crs "data/raw/BXW/$product.tif" --expected-radius-m 3396190 --out "$t1_metadata_dir/crs-$product.json"
done
for resolution in 1 4; do
    if [[ "$resolution" == 1 ]]; then
        primary="data/derived/BXW/dem_enu.tif"
        reference="data/derived/BXW/hirise_019698_enu.tif"
    else
        primary="data/derived/BXW/dem_plan_4m.tif"
        reference="data/derived/BXW/hirise_019698_plan_4m.tif"
    fi
    cli "enu-gale-$resolution" enu data/raw/BXW/gale_dem_v3.tif --site BXW --expected-radius-m 3396190 --h0-m 0 --resolution-m "$resolution" --out "$primary"
    cli "enu-hirise-$resolution" enu data/raw/BXW/hirise_dtm_bxw_019698.tif --site BXW --expected-radius-m 3396190 --h0-m 0 --resolution-m "$resolution" --out "$reference"
done
cli derive derive data/derived/BXW/dem_enu.tif --out data/derived/BXW/terrain
# Pair-specific bound justified by fixed-support coarse diagnostic; the library
# default remains20m and rejects this pair. Never use80m as a general default.
cli compare compare data/derived/BXW/dem_enu.tif data/derived/BXW/hirise_019698_enu.tif \
    data/derived/BXW/dem_plan_4m.tif data/derived/BXW/hirise_019698_plan_4m.tif \
    --vertical-evidence docs/verification/T1_VERTICAL_DATUM.json --max-shift-m 80 --out data/derived/BXW/comparison
cli qa-1m qa data/raw/BXW/gale_dem_v3.tif data/derived/BXW/dem_enu.tif --terrain data/derived/BXW/terrain --out data/derived/BXW/qa_1m
cli qa-4m qa data/raw/BXW/gale_dem_v3.tif data/derived/BXW/dem_plan_4m.tif --out data/derived/BXW/qa_4m
bash scripts/test-data.sh | tee "$t1_log_dir/tests.log"
data_evidence_line="$(tail -n 1 "$t1_log_dir/tests.log")"
if [[ "$data_evidence_line" != "Data test evidence: "* ]]; then
    printf 'Missing successful data-test evidence line\n' >&2
    exit 1
fi
data_test_dir="${data_evidence_line#Data test evidence: }"
env -u PYTHONPATH "$REDLINE_VENV/bin/python" scripts/record_data_run.py --site BXW --include-comparison \
    --test-report "$data_test_dir/python.xml" --out "$t1_metadata_dir/run_manifest.json"
cli stac stac --site BXW --manifest "$t1_metadata_dir/run_manifest.json" --out "$t1_metadata_dir/catalog"
cli stac-validation stac-validate "$t1_metadata_dir/catalog" --out "$t1_metadata_dir/stac_validation.json"
cli qa-final qa-final --manifest "$t1_metadata_dir/run_manifest.json" --stac "$t1_metadata_dir/catalog" \
    --out "data/derived/BXW/$t1_run_key"
printf 'T1 accepted. Metadata: %s\n' "$t1_metadata_dir"
printf 'QA: %s/data/derived/BXW/%s/qa_BXW.html\n' "$REDLINE_ROOT" "$t1_run_key"
