#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
redline_load_runtime
export GZ_PARTITION="redline_t3_sensor_probe_$$"
mkdir -p "$REDLINE_TEST_RESULTS"
probe_dir="$(mktemp -d "$REDLINE_TEST_RESULTS/t3-sensors-XXXXXXXX")"
export REDLINE_T3_PROBE_DIR="$probe_dir"
"$REDLINE_SYSTEM_PYTHON" - <<'PY'
import json, os, pathlib, signal, subprocess, time
out = pathlib.Path(os.environ['REDLINE_T3_PROBE_DIR'])
world = '/opt/ros/jazzy/opt/gz_sim_vendor/share/gz/gz-sim8/worlds/sensors_demo.sdf'
log = (out/'gazebo.log').open('w')
server = subprocess.Popen(['gz','sim','-s','-r','--headless-rendering','-v','3',world],
                          stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
result = {'world':world,'partition':os.environ['GZ_PARTITION'],'passed':False}
try:
    deadline = time.monotonic()+40
    while time.monotonic()<deadline:
        if server.poll() is not None:
            raise RuntimeError(f'Gazebo exited {server.returncode}')
        topics = subprocess.run(['gz','topic','-l'],capture_output=True,text=True,timeout=5).stdout.splitlines()
        if '/camera' in topics:
            try:
                sample = subprocess.run(['gz','topic','-e','-t','/camera','-n','1','--json-output'],
                    capture_output=True,text=True,timeout=8,check=True)
                value = json.loads(sample.stdout)
                result.update(passed=True,camera_width=value.get('width'),camera_height=value.get('height'),
                              camera_pixel_format=value.get('pixelFormatType'),topics=topics)
                break
            except subprocess.TimeoutExpired:
                pass
        time.sleep(.5)
    if not result['passed']:
        raise RuntimeError('No rendered camera message within the bounded probe')
finally:
    os.killpg(server.pid,signal.SIGINT)
    try: server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(server.pid,signal.SIGKILL)
        server.wait()
    log.close()
    result['log']=str(out/'gazebo.log')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
PY
