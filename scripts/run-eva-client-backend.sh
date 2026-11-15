#!/usr/bin/env bash
# Human gameplay backend, isolated from the rover graph. No simulated pose publisher.
# Usage: bash scripts/run-eva-client-backend.sh <verified T5 workspace> [hold seconds]
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
workspace="$(realpath -- "${1:?T5 workspace required}")"
hold_s="${2:-1800}"
[[ "$hold_s" =~ ^[0-9]+$ ]] && ((hold_s >= 1 && hold_s <= 3600)) || exit 2
redline_load_runtime
set +u
source "$workspace/install/local_setup.bash"
set -u
export ROS_DOMAIN_ID="${EVA_DOMAIN_ID:-87}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
port="${EVA_PORT:-9290}"
bind="$(hostname -I | awk '{print $1}')"
evidence="$(mktemp -d "$REDLINE_TEST_RESULTS/eva-client-XXXXXXXX")"
env -u PYTHONPATH "$REDLINE_VENV/bin/python" "$REDLINE_ROOT/scripts/prepare_eva_runtime.py" >"$evidence/profile.log"
sprint_cap="$(env -u PYTHONPATH "$REDLINE_VENV/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["gameplay_locomotion"]["sprint_cap_m_s"])' "$REDLINE_ROOT/data/engines/BXW/eva-runtime-v1.json")"
args=("redline_root:=$REDLINE_ROOT" "python:=$REDLINE_VENV/bin/python" rosbridge:=false planner:=false "time_scale:=${EVA_TIME_SCALE:-1}" "scenario_pose_speed_cap_m_s:=$sprint_cap")
if [[ "${EVA_MODE:-T5}" == S1 ]]; then
    sed -e "s/^time_scale: .*/time_scale: ${EVA_TIME_SCALE:-60}/" "$REDLINE_ROOT/config/scenarios/S1_SEP_4190.yaml" >"$evidence/S1.yaml"
    args+=("scenario_file:=$evidence/S1.yaml" "sun_table:=$REDLINE_ROOT/data/env/sun_BXW_2024-05-19_22.csv")
elif [[ "${EVA_MODE:-T5}" != T5 ]]; then
    echo 'EVA_MODE must be T5 or S1' >&2;exit 2
else
    args+=("intro:=${EVA_INTRO:-true}")
fi
pids=()
printf '%s\n' "$BASHPID" >"$evidence/supervisor.pid"
stop() {
    trap - EXIT INT TERM
    for pid in "${pids[@]}";do kill -INT -- "-$pid" 2>/dev/null || true;done
    for _ in $(seq 60);do
        alive=0
        for pid in "${pids[@]}";do kill -0 -- "-$pid" 2>/dev/null && alive=1;done
        ((alive == 0)) && break
        sleep .1
    done
    # Only process groups created above. Some rosbridge releases retain their
    # asyncio listener after SIGINT; do not leave it occupying the next run's port.
    for pid in "${pids[@]}";do kill -KILL -- "-$pid" 2>/dev/null || true;done
}
trap stop EXIT INT TERM
setsid ros2 launch redline_planner t5_thread.launch.py "${args[@]}" >"$evidence/launch.log" 2>&1 &
pids+=("$!")
printf '%s\n' "${pids[@]}" >"$evidence/process-groups.txt"
setsid ros2 launch rosbridge_server rosbridge_websocket_launch.xml "port:=$port" "address:=$bind" 'url_path:=/+' >"$evidence/bridge.log" 2>&1 &
pids+=("$!")
printf '%s\n' "${pids[@]}" >"$evidence/process-groups.txt"
printf 'EVA evidence: %s\nEVA URL: ws://%s:%s/\nDomain: %s; mode: %s\n' "$evidence" "$bind" "$port" "$ROS_DOMAIN_ID" "${EVA_MODE:-T5}"
sleep "$hold_s" & wait "$!"
