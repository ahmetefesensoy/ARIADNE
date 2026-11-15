#!/usr/bin/env bash
# One bounded campaign session; only the process groups it creates are stopped.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
workspace="$(realpath -- "${1:?verified combined workspace required}")"
hold_s="${2:-3600}"
[[ "$hold_s" =~ ^[0-9]+$ ]] && ((hold_s >= 1 && hold_s <= 3600)) || exit 2
rviz_enabled="${CAMPAIGN_RVIZ:-0}"
[[ "$rviz_enabled" == 0 || "$rviz_enabled" == 1 ]] || { printf 'CAMPAIGN_RVIZ must be 0 or 1\n' >&2; exit 2; }
rviz_driver="${CAMPAIGN_RVIZ_DRIVER:-llvmpipe}"
[[ "$rviz_driver" == llvmpipe || "$rviz_driver" == d3d12 ]] || { printf 'CAMPAIGN_RVIZ_DRIVER must be llvmpipe or d3d12\n' >&2; exit 2; }
redline_load_runtime
set +u
source "$workspace/install/local_setup.bash"
set -u
export ROS_DOMAIN_ID="${CAMPAIGN_DOMAIN_ID:-137}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
port="${CAMPAIGN_PORT:-9390}"
evidence="$(mktemp -d "$REDLINE_TEST_RESULTS/campaign-XXXXXXXX")"
export GZ_PARTITION="redline-campaign-$(basename "$evidence")"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-BXW_CAMPAIGN-15"
printf '%s\n' "$BASHPID" >"$evidence/supervisor.pid"
py="$REDLINE_VENV/bin/python"
env -u PYTHONPATH "$py" "$REDLINE_ROOT/scripts/prepare_eva_runtime.py" >"$evidence/eva-profile.log"
env -u PYTHONPATH "$py" "$REDLINE_ROOT/scripts/prepare_campaign_runtime.py" --profile "${CAMPAIGN_FIELD_PROFILE:-field}" --out "$evidence/inputs" >"$evidence/placement.log"
view_args=()
if [[ "$rviz_enabled" == 1 ]];then
    env -u PYTHONPATH "$py" "$REDLINE_ROOT/scripts/prepare_campaign_rviz.py" \
        --terrain "$evidence/inputs/terrain.json" --out "$evidence/rviz/campaign.rviz" >"$evidence/rviz-stage.log"
    view_args=(--navigation-view --rviz-config "$evidence/rviz/campaign.rviz" --rviz-driver "$rviz_driver")
fi
if [[ "${CAMPAIGN_TABLET_STREAM:-1}" == 1 ]];then
    # Always use a private X server; never stream the user's desktop.
    if ! command -v xvfb-run >/dev/null;then printf 'Tablet RViz stream needs the official xvfb package\n' >&2;exit 2;fi
    if [[ ! -f "$evidence/rviz/campaign.rviz" ]];then
        env -u PYTHONPATH "$py" "$REDLINE_ROOT/scripts/prepare_campaign_rviz.py" --terrain "$evidence/inputs/terrain.json" --out "$evidence/rviz/campaign.rviz" >"$evidence/rviz-stage.log"
    fi
    if [[ "$rviz_enabled" == 0 ]];then view_args=(--navigation-view);fi
fi
bind="$(hostname -I | awk '{print $1}')"
pids=()
stream_pid=""
stop() {
    trap - EXIT INT TERM
    for pid in "${pids[@]}";do
        if [[ "$pid" == "$stream_pid" ]];then kill -INT -- "-$pid" 2>/dev/null || true
        else kill -INT "$pid" 2>/dev/null || true;fi
    done
    # t3_supervisor owns nested ros2 launch groups and allows them 12 s to
    # stop. Give that owner enough time before escalating its process group.
    for _ in $(seq 250);do
        alive=0;for pid in "${pids[@]}";do kill -0 "$pid" 2>/dev/null && alive=1;done
        ((alive == 0)) && break;sleep .1
    done
    for pid in "${pids[@]}";do kill -KILL -- "-$pid" 2>/dev/null || true;done
}
trap stop EXIT INT TERM
mkdir -p "$evidence/robot"
scout_mode="${CAMPAIGN_SCOUT_MODE:-stub}"
scout_args=()
if [[ "$scout_mode" == physical ]];then scout_args=(--scout-model "$evidence/inputs/scout_1.sdf");fi
setsid "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/t3_supervisor.py" --workspace "$workspace" \
    --out "$evidence/robot" --terrain "$evidence/inputs/terrain.json" --delivered-rover \
    --controller rpp --stationary-hold "$hold_s" "${scout_args[@]}" "${view_args[@]}" >"$evidence/robot-supervisor.log" 2>&1 &
pids+=("$!")
setsid "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/gazebo_presentation.py" --read-only \
    --report-out "$evidence/presentation.json" >"$evidence/presentation.log" 2>&1 &
pids+=("$!")
setsid ros2 launch redline_planner campaign.launch.py "redline_root:=$REDLINE_ROOT" "python:=$py" \
    "targets_file:=$evidence/inputs/targets_BXW.yaml" "run_id:=$run_id" "scout_mode:=$scout_mode" >"$evidence/campaign.log" 2>&1 &
pids+=("$!")
export T4_ROSBRIDGE_ADDRESS="$bind" T4_ROSBRIDGE_PORT="$port" T4_BRIDGE_MAX_SECONDS="$hold_s"
if [[ "${CAMPAIGN_TABLET_STREAM:-1}" == 1 ]];then
    setsid env QT_QPA_PLATFORM=xcb xvfb-run -a -s '-screen 0 1024x640x24 -nolisten tcp' "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/rviz_tablet_stream.py" --config "$evidence/rviz/campaign.rviz" --out "$evidence/rviz-stream" --seconds "$hold_s" >"$evidence/rviz-stream.log" 2>&1 &
    stream_pid="$!";pids+=("$stream_pid")
fi
setsid "$REDLINE_SYSTEM_PYTHON" "$REDLINE_ROOT/scripts/t4_bridge_runtime.py" >"$evidence/bridge.log" 2>&1 &
pids+=("$!")
printf '%s\n' "${pids[@]}" >"$evidence/process-groups.txt"
printf 'Campaign evidence: %s\nCampaign URL: ws://%s:%s/\nDomain: %s; GZ partition: %s\n' "$evidence" "$bind" "$port" "$ROS_DOMAIN_ID" "$GZ_PARTITION"
printf 'Passive RViz: %s (same domain and physics world)\n' "$rviz_enabled"
sleep "$hold_s" & wait "$!"
