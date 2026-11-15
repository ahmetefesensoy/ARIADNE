#!/usr/bin/env bash
# T5 BXW steel-thread run through rosbridge (proje.md §18 T5; D009). No Gazebo, no Unreal.
# Usage: bash scripts/run-t5-bxw.sh <built-workspace>   (from scripts/build-t5.sh)
# A separate domain and port keep this run off any T3/T4 graph on domain 77 / port 9090.
# Writes runs/<run_id>/ue_feed.jsonl (UE offline feed) and test-results/t5-bxw-<run_id>/.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
if [[ $# -lt 1 ]]; then
    printf 'Usage: bash scripts/run-t5-bxw.sh <built-workspace>\n' >&2
    exit 2
fi
workspace="$(realpath -- "$1")"
redline_load_runtime
set +u
source "$workspace/install/local_setup.bash"
set -u
export ROS_DOMAIN_ID="${T5_DOMAIN_ID:-86}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
port="${T5_ROSBRIDGE_PORT:-9190}"
time_scale="${T5_TIME_SCALE:-60}"
return_min="${T5_WALK_RETURN_MIN:-3}"
hold_s="${T5_HOLD_S:-30}"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-T5_THREAD_BXW-0"
evidence="$REDLINE_TEST_RESULTS/t5-bxw-$run_id"
feed_dir="$REDLINE_ROOT/runs/$run_id"
mkdir -p "$evidence" "$feed_dir"
py="$REDLINE_VENV/bin/python"

env -u PYTHONPATH "$py" "$REDLINE_ROOT/scripts/t5_walk_path.py" --return-min "$return_min" \
    --out "$evidence/walk_path.json" | tee "$evidence/walk_path.stdout"

setsid ros2 launch redline_planner t5_thread.launch.py rosbridge:=true "rosbridge_port:=$port" \
    "time_scale:=$time_scale" "redline_root:=$REDLINE_ROOT" "python:=$py" >"$evidence/launch.log" 2>&1 &
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
    if grep -q "startup" "$evidence/launch.log" && (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
        break
    fi
    kill -0 "$launch_pid" 2>/dev/null || { cat "$evidence/launch.log" >&2; exit 1; }
    sleep 1
done
sleep 3
walk_s="$(python3 -c "import json,math,sys; p=json.load(open(sys.argv[1]))['waypoints_xy_m']; \
print(sum(math.dist(a,b) for a,b in zip(p,p[1:]))/0.8)" "$evidence/walk_path.json")"
duration="$(python3 -c "print(round($walk_s + $hold_s + 20))")"

python3 "$REDLINE_ROOT/scripts/t4_capture_feed.py" --url "ws://localhost:$port" \
    --topic /redline/redline=redline_msgs/msg/RedLine \
    --topic /redline/tiles/margin_min=redline_msgs/msg/FieldTile \
    --topic /redline/mission/clock=rosgraph_msgs/msg/Clock \
    --topic /crew/EV1/state=redline_msgs/msg/CrewState \
    --duration "$duration" --throttle-ms 0 --source-status SCENARIO \
    --source-note "T5 BXW thread: DERIVED terrain, SCENARIO crew/suit/EVA, SIMULATED Unreal stand-in walk" \
    --output "$feed_dir/ue_feed.jsonl" --report "$evidence/capture.json" >"$evidence/capture.stdout" 2>&1 &
capture_pid=$!
sleep 2
python3 "$REDLINE_ROOT/scripts/t5_rosbridge_walker.py" --url "ws://localhost:$port" \
    --waypoints "$evidence/walk_path.json" --speed 0.8 --hold-s "$hold_s" --report "$evidence/walker.json" \
    2>&1 | tee "$evidence/walker.log"  # pipefail (set -o pipefail) keeps a walker failure fatal
timeout 6 ros2 topic echo /diagnostics diagnostic_msgs/msg/DiagnosticArray >"$evidence/diagnostics.txt" 2>&1 || true
wait "$capture_pid"
stop
trap - EXIT
env -u PYTHONPATH "$py" "$REDLINE_ROOT/scripts/t5_feed_summary.py" "$feed_dir/ue_feed.jsonl" \
    --out "$evidence/feed_summary.json"
sha256sum "$feed_dir/ue_feed.jsonl" | tee "$evidence/ue_feed.sha256"
printf 'T5 BXW evidence: %s\nUE feed: %s\n' "$evidence" "$feed_dir/ue_feed.jsonl"
