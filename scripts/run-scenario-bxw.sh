#!/usr/bin/env bash
# A nominal-flow scenario (initial_phase before TRAVERSE) on the real BXW grid through rosbridge (D015).
# Usage: bash scripts/run-scenario-bxw.sh <config/scenarios/X.yaml> <built-workspace>
# planner_server makes plan v1 in BRIEFING; every crew member walks it (ev_sim plan mode, SIMULATED);
# mission_manager starts mission time at egress, so the capture is up before PET moves.
# S1 (starts mid-EVA, crew from Unreal or a walker client) keeps scripts/run-s1-bxw.sh.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# -ge 2 ]] || { printf 'Usage: bash scripts/run-scenario-bxw.sh <scenario.yaml> <built-workspace>\n' >&2; exit 2; }
scenario_src="$(realpath -- "$1")"
workspace="$(realpath -- "$2")"
redline_load_runtime
set +u
source "$workspace/install/local_setup.bash"
set -u
export ROS_DOMAIN_ID="${SCN_DOMAIN_ID:-86}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
port="${SCN_ROSBRIDGE_PORT:-9190}"
py="$REDLINE_VENV/bin/python"
scenario_id="$(env -u PYTHONPATH "$py" -c 'import sys, yaml; d = yaml.safe_load(open(sys.argv[1])); print(d["id"] + "-" + str(d["seed"]))' "$scenario_src")"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-$scenario_id"
evidence="$REDLINE_TEST_RESULTS/scn-bxw-$run_id"
feed_dir="$REDLINE_ROOT/runs/$run_id"
mkdir -p "$evidence" "$feed_dir"
cp -- "$scenario_src" "$evidence/scenario.yaml"
crew_topics=()
for crew in $(env -u PYTHONPATH "$py" -c 'import sys, yaml; print(" ".join(yaml.safe_load(open(sys.argv[1]))["crew"]))' "$scenario_src"); do
    crew_topics+=(--topic "/crew/$crew/state=redline_msgs/msg/CrewState")
done

setsid ros2 launch redline_planner t5_thread.launch.py rosbridge:=true "rosbridge_port:=$port" planner:=true \
    "redline_root:=$REDLINE_ROOT" "python:=$py" "scenario_file:=$evidence/scenario.yaml" \
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
    --topic /redline/decisions=redline_msgs/msg/DecisionRecord \
    --topic /redline/plan=redline_msgs/msg/EVAPlan \
    --topic /redline/redline=redline_msgs/msg/RedLine \
    "${crew_topics[@]}" \
    --duration "${SCN_CAPTURE_S:-420}" --throttle-ms 0 --min-messages 1 --source-status SCENARIO \
    --source-note "BXW scenario $scenario_id: ARCHIVE RAD, DERIVED terrain/sun, SCENARIO plan/crew/rules, SIMULATED crew walk" \
    --output "$feed_dir/ue_feed.jsonl" --report "$evidence/capture.json" >"$evidence/capture.stdout" 2>&1 &
capture_pid=$!
wait "$capture_pid" || true
timeout 6 ros2 topic echo /diagnostics diagnostic_msgs/msg/DiagnosticArray >"$evidence/diagnostics.txt" 2>&1 || true
stop
trap - EXIT
env -u PYTHONPATH "$py" "$REDLINE_ROOT/scripts/scenario_feed_summary.py" "$feed_dir/ue_feed.jsonl" \
    --scenario "$evidence/scenario.yaml" --out "$evidence/summary.json"
sha256sum "$feed_dir/ue_feed.jsonl" | tee "$evidence/ue_feed.sha256"
printf 'Scenario evidence: %s\nUE feed: %s\n' "$evidence" "$feed_dir/ue_feed.jsonl"
