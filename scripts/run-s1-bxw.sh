#!/usr/bin/env bash
# S1 on the real BXW grid with the real RAD sol 4190 replay, through rosbridge (proje.md §16, T6; D012).
# Usage: bash scripts/run-s1-bxw.sh <built-workspace>
# The scenario is config/scenarios/S1_SEP_4190.yaml with time_scale raised to T6_TIME_SCALE (default 60)
# so the real alarm (PET 111.8 min) arrives ~2 min after start; the copy is kept in the evidence folder.
# A SIMULATED rosbridge client plays EV1: walks out, waits, walks home when the mission orders RETURN.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# -ge 1 ]] || { printf 'Usage: bash scripts/run-s1-bxw.sh <built-workspace>\n' >&2; exit 2; }
workspace="$(realpath -- "$1")"
redline_load_runtime
set +u
source "$workspace/install/local_setup.bash"
set -u
export ROS_DOMAIN_ID="${T6_DOMAIN_ID:-86}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
port="${T6_ROSBRIDGE_PORT:-9190}"
scale="${T6_TIME_SCALE:-60}"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-S1_SEP_4190-42"
evidence="$REDLINE_TEST_RESULTS/s1-bxw-$run_id"
feed_dir="$REDLINE_ROOT/runs/$run_id"
mkdir -p "$evidence" "$feed_dir"
py="$REDLINE_VENV/bin/python"
sed -e "s/^time_scale: .*/time_scale: $scale  # run-s1-bxw.sh override of 10/" \
    "$REDLINE_ROOT/config/scenarios/S1_SEP_4190.yaml" > "$evidence/S1_SEP_4190.yaml"
env -u PYTHONPATH "$py" "$REDLINE_ROOT/scripts/t5_walk_path.py" --return-min 1.5 \
    --out "$evidence/walk_path.json" | tee "$evidence/walk_path.stdout"

setsid ros2 launch redline_planner t5_thread.launch.py rosbridge:=true "rosbridge_port:=$port" \
    "redline_root:=$REDLINE_ROOT" "python:=$py" "scenario_file:=$evidence/S1_SEP_4190.yaml" \
    "sun_table:=$REDLINE_ROOT/data/env/sun_BXW_2024-05-19_22.csv" \
    >"$evidence/launch.log" 2>&1 &
launch_pid=$!
stop() {
    if kill -0 "$launch_pid" 2>/dev/null; then
        kill -INT -- "-$launch_pid" 2>/dev/null || true
        for _ in $(seq 40); do kill -0 "$launch_pid" 2>/dev/null || break; sleep 0.5; done
        kill -KILL -- "-$launch_pid" 2>/dev/null || true
    fi
}
trap stop EXIT
for _ in $(seq 120); do
    (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null && break
    kill -0 "$launch_pid" 2>/dev/null || { cat "$evidence/launch.log" >&2; exit 1; }
    sleep 1
done
python3 "$REDLINE_ROOT/scripts/t4_capture_feed.py" --url "ws://localhost:$port" \
    --topic /redline/mission/clock=rosgraph_msgs/msg/Clock \
    --topic /env/dose_rate=redline_msgs/msg/DoseRate \
    --topic /env/state=redline_msgs/msg/EnvState \
    --topic /redline/mission/state=redline_msgs/msg/MissionState \
    --topic /redline/alerts=redline_msgs/msg/Alert \
    --topic /safety/violations=redline_msgs/msg/RuleViolation \
    --topic /redline/scenario/event=redline_msgs/msg/Alert \
    --topic /redline/redline=redline_msgs/msg/RedLine \
    --topic /redline/tiles/margin_min=redline_msgs/msg/FieldTile \
    --duration "${T6_CAPTURE_S:-330}" --throttle-ms 0 --min-messages 1 --source-status SCENARIO \
    --source-note "S1 BXW: ARCHIVE RAD sol 4189-4191, DERIVED terrain, SCENARIO crew/suit/rules, SIMULATED EV1 client" \
    --output "$feed_dir/ue_feed.jsonl" --report "$evidence/capture.json" >"$evidence/capture.stdout" 2>&1 &
capture_pid=$!
sleep 2
python3 "$REDLINE_ROOT/scripts/t5_rosbridge_walker.py" --url "ws://localhost:$port" \
    --waypoints "$evidence/walk_path.json" --speed 0.8 --return-on-phase --max-wait-s 400 --hold-s 20 \
    --report "$evidence/walker.json" 2>&1 | tee "$evidence/walker.log"
timeout 6 ros2 topic echo /diagnostics diagnostic_msgs/msg/DiagnosticArray >"$evidence/diagnostics.txt" 2>&1 || true
wait "$capture_pid"
stop
trap - EXIT
python3 "$REDLINE_ROOT/scripts/s1_feed_summary.py" "$feed_dir/ue_feed.jsonl" --out "$evidence/s1_summary.json"
sha256sum "$feed_dir/ue_feed.jsonl" | tee "$evidence/ue_feed.sha256"
printf 'S1 BXW evidence: %s\nUE feed: %s\n' "$evidence" "$feed_dir/ue_feed.jsonl"
