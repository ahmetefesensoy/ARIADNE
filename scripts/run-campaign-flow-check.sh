#!/usr/bin/env bash
# Background 12-step campaign check: starts one campaign backend (physical scout, Gazebo/Nav2),
# runs scripts/verify_campaign_flow.py against it (SIMULATED human stand-in, actual ROS robots and
# science chain), then stops only what it started. No Unreal player is needed.
# Usage: bash scripts/run-campaign-flow-check.sh <verified-workspace>
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
workspace="$(realpath -- "${1:?verified combined workspace required}")"
redline_load_runtime
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$REDLINE_TEST_RESULTS/campaign-flow-$stamp"
mkdir -p "$out"
CAMPAIGN_SCOUT_MODE="${CAMPAIGN_SCOUT_MODE:-physical}" setsid bash "$REDLINE_ROOT/scripts/run-campaign-backend.sh" "$workspace" 3600 >"$out/backend.log" 2>&1 &
backend=$!
cleanup() { kill -INT -- "-$backend" 2>/dev/null || true; for _ in $(seq 60); do kill -0 -- "-$backend" 2>/dev/null || return 0; sleep 1; done; kill -KILL -- "-$backend" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
url="" evidence=""
for _ in $(seq 300); do
    url="$(sed -n 's/^Campaign URL: //p' "$out/backend.log" | tail -1)"
    evidence="$(sed -n 's/^Campaign evidence: //p' "$out/backend.log" | tail -1)"
    [[ -n "$url" && -n "$evidence" ]] && break
    kill -0 "$backend" 2>/dev/null || { echo "backend exited early" >&2; tail -30 "$out/backend.log" >&2; exit 1; }
    sleep 1
done
[[ -n "$url" ]] || { echo "campaign URL never appeared" >&2; exit 1; }
printf 'backend ready: %s (evidence %s)\n' "$url" "$evidence" | tee "$out/status.txt"
# Gazebo world, rover Nav2 and the physical scout need minutes to come up.
sleep 180
python3 "$REDLINE_ROOT/scripts/verify_campaign_flow.py" --url "$url" \
    --targets "$evidence/inputs/targets_BXW.yaml" --out "$out/flow" 2>&1 | tee "$out/flow.log"
status=${PIPESTATUS[0]}
printf 'flow exit %s; report: %s/flow\n' "$status" "$out" | tee -a "$out/status.txt"
exit "$status"
