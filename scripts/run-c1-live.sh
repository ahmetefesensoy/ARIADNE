#!/usr/bin/env bash
# C1: the short sol 4190 chapter (config/scenarios/C1_SOL4190_CHAPTER.yaml) at x1 on the real BXW grid.
# The EVA starts at historical 05:10:00 UTC, so the first ARCHIVE RAD E alarm (05:21:50 UTC) arrives at
# PET 11.8 min; dose data is not shifted (D018). Same backend as S1 (t5_thread + scenario_file).
#
# Usage: bash scripts/run-c1-live.sh <built-workspace>
#   Default: EV1 is the live Unreal client (scripts/start-t5-eva.ps1 -RosbridgeUrl ws://<wsl-ip>:9190/
#            -SkipPrologue). Walk out about 300 m before PET 11.8 min, then go home when told.
#   C1_WALKER=1: a SIMULATED rosbridge client plays EV1 instead (headless check of the same chain).
# Env: C1_DOMAIN_ID (86), C1_ROSBRIDGE_PORT (9190), C1_CAPTURE_S (1500), C1_RETURN_MIN (10).
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# -ge 1 ]] || { printf 'Usage: bash scripts/run-c1-live.sh <built-workspace>\n' >&2; exit 2; }
workspace="$(realpath -- "$1")"
redline_load_runtime
set +u
source "$workspace/install/local_setup.bash"
set -u
export ROS_DOMAIN_ID="${C1_DOMAIN_ID:-86}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
port="${C1_ROSBRIDGE_PORT:-9190}"
walker="${C1_WALKER:-0}"
if [[ "$walker" == 1 ]]; then crew_note="SIMULATED EV1 client"; else crew_note="actual Unreal EV1"; fi
scenario_file="${C1_SCENARIO:-$REDLINE_ROOT/config/scenarios/C1_SOL4190_CHAPTER.yaml}"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-$(basename "$scenario_file" .yaml)-42"
evidence="$REDLINE_TEST_RESULTS/c1-bxw-$run_id"
feed_dir="$REDLINE_ROOT/runs/$run_id"
mkdir -p "$evidence" "$feed_dir"
py="$REDLINE_VENV/bin/python"
cp -- "$scenario_file" "$evidence/scenario.yaml"

# The Unreal client reaches rosbridge on the WSL address (as run-eva-client-backend.sh does); the
# simulated walker stays on loopback inside the launch.
if [[ "$walker" == 1 ]]; then
    bind=127.0.0.1
    bridge_args=(rosbridge:=true "rosbridge_port:=$port")
else
    bind="$(hostname -I | awk '{print $1}')"
    bridge_args=(rosbridge:=false)
fi
pids=()
stop() {
    local pid alive
    for pid in "${pids[@]}"; do kill -INT -- "-$pid" 2>/dev/null || true; done
    for _ in $(seq 40); do
        alive=0
        for pid in "${pids[@]}"; do kill -0 -- "-$pid" 2>/dev/null && alive=1; done
        ((alive == 0)) && break
        sleep 0.5
    done
    for pid in "${pids[@]}"; do kill -KILL -- "-$pid" 2>/dev/null || true; done
}
trap stop EXIT INT TERM
setsid ros2 launch redline_planner t5_thread.launch.py "${bridge_args[@]}" \
    "redline_root:=$REDLINE_ROOT" "python:=$py" "scenario_file:=$evidence/scenario.yaml"     "sun_table:=$REDLINE_ROOT/data/env/sun_BXW_2024-05-19_22.csv"     >"$evidence/launch.log" 2>&1 &
pids+=("$!")
if [[ "$walker" != 1 ]]; then
    setsid ros2 launch rosbridge_server rosbridge_websocket_launch.xml "port:=$port" "address:=$bind" 'url_path:=/+' \
        >"$evidence/bridge.log" 2>&1 &
    pids+=("$!")
fi
for _ in $(seq 120); do
    (exec 3<>"/dev/tcp/$bind/$port") 2>/dev/null && break
    kill -0 -- "-${pids[0]}" 2>/dev/null || { cat "$evidence/launch.log" >&2; exit 1; }
    sleep 1
done
printf 'C1 backend ready: ws://%s:%s/ (domain %s, %s)\n' "$bind" "$port" "$ROS_DOMAIN_ID" "$crew_note"
python3 "$REDLINE_ROOT/scripts/t4_capture_feed.py" --url "ws://$bind:$port/" \
    --topic /redline/mission/clock=rosgraph_msgs/msg/Clock \
    --topic /env/dose_rate=redline_msgs/msg/DoseRate \
    --topic /env/state=redline_msgs/msg/EnvState \
    --topic /redline/mission/state=redline_msgs/msg/MissionState \
    --topic /redline/alerts=redline_msgs/msg/Alert \
    --topic /safety/violations=redline_msgs/msg/RuleViolation \
    --topic /redline/scenario/event=redline_msgs/msg/Alert \
    --topic /redline/redline=redline_msgs/msg/RedLine \
    --topic /redline/tiles/margin_min=redline_msgs/msg/FieldTile \
    --topic /crew/EV1/pose=geometry_msgs/msg/PoseStamped \
    --duration "${C1_CAPTURE_S:-1500}" --throttle-ms 0 --min-messages 1 --source-status SCENARIO \
    --source-note "C1 BXW: ARCHIVE RAD sol 4189-4191, DERIVED terrain, SCENARIO crew/suit/rules, $crew_note" \
    --output "$feed_dir/ue_feed.jsonl" --report "$evidence/capture.json" >"$evidence/capture.stdout" 2>&1 &
capture_pid=$!
if [[ "$walker" == 1 ]]; then
    env -u PYTHONPATH "$py" "$REDLINE_ROOT/scripts/t5_walk_path.py" --return-min "${C1_RETURN_MIN:-10}" \
        --out "$evidence/walk_path.json" | tee "$evidence/walk_path.stdout"
    sleep 2
    python3 "$REDLINE_ROOT/scripts/t5_rosbridge_walker.py" --url "ws://localhost:$port" \
        --waypoints "$evidence/walk_path.json" --speed 0.8 --return-on-phase --max-wait-s 1200 --hold-s 20 \
        --report "$evidence/walker.json" 2>&1 | tee "$evidence/walker.log"
fi
wait "$capture_pid" || true
stop
trap - EXIT
python3 "$REDLINE_ROOT/scripts/s1_feed_summary.py" "$feed_dir/ue_feed.jsonl" --out "$evidence/c1_summary.json"
sha256sum "$feed_dir/ue_feed.jsonl" | tee "$evidence/ue_feed.sha256"
printf 'C1 BXW evidence: %s\nUE feed: %s\n' "$evidence" "$feed_dir/ue_feed.jsonl"
