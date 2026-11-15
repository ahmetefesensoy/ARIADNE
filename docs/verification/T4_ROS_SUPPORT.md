# T4 rosbridge transport support

The WSL ROS bridge dependency and transport helpers are ready. Two isolated
websocket integration tests pass. These checks establish the capture and test
server behavior; they do not establish a ROS-to-Unreal connection or T4 acceptance.

Recorded on 2026-11-14 in WSL2 `Ubuntu-24.04`, Ubuntu 24.04.5, user
`ahmetefesensoy`, Python 3.12.3. No ROS graph, action goal, rover motion or Unreal
process was started by this support task. Runtime starts remain coordinated by
the main integration task.

## Installed dependency evidence

The packages were absent at inventory and installed from the configured Ubuntu
and ROS apt repositories with WSL root. The existing Jazzy runtime was retained.

| Package | Observed installed version |
|---|---|
| `ros-jazzy-rosbridge-suite` | `2.7.1-1noble.20261006.035549` |
| `ros-jazzy-rosbridge-server` | `2.7.1-1noble.20261006.035306` |
| `ros-jazzy-rosbridge-library` | `2.7.1-1noble.20260912.164625` |
| `ros-jazzy-rosapi` | `2.7.1-1noble.20261006.034805` |
| `python3-websockets` | `10.4-1` |

Local evidence is in `test-results/t4-ros-support-inventory.json`. The resolved
Python websocket module is `/usr/lib/python3/dist-packages/websockets/__init__.py`.

## Launch and capture interfaces

Run the launcher from the repository with an explicitly selected, already-built
ASCII ROS workspace. It sources the Jazzy underlay and that workspace's local
overlay, then starts only the installed rosbridge launch file. The default
domain is 77; the default listener is `127.0.0.1:9090`.

```bash
bash scripts/t4_rosbridge.sh /absolute/path/to/built-workspace
# Optional listener configuration:
T4_ROSBRIDGE_PORT=9090 T4_ROSBRIDGE_ADDRESS=127.0.0.1 \
  bash scripts/t4_rosbridge.sh /absolute/path/to/built-workspace
```

Launch arguments were inspected without executing nodes:
`bash scripts/t4_rosbridge.sh <built-workspace> --show-args` exited 0 and resolved
`rosbridge_server` to `/opt/ros/jazzy`. Output is retained in
`test-results/t4-rosbridge-launch-arguments.txt`.

The capture client sends only `subscribe` and `unsubscribe` operations. It never
publishes a ROS message or calls a service/action. The default topic is
`/rover_1/odom=nav_msgs/msg/Odometry`; repeat `--topic` for more. A recording
requires at least two messages from every requested topic unless
`--min-messages` is changed explicitly.

```bash
python3 scripts/t4_capture_feed.py \
  --url ws://localhost:9090 \
  --topic /rover_1/odom=nav_msgs/msg/Odometry \
  --duration 10 \
  --source-status SIMULATED --source-note 'Gazebo authoritative rover odometry' \
  --output runs/<run_id>/ue_feed.jsonl \
  --report test-results/t4-real-capture.json
```

Each JSONL line is a rosbridge `publish` envelope with the original ROS `msg`
values and an added top-level `_redline_elapsed_sec`: monotonic receipt seconds
from the first captured publish, starting at zero. This field is outside `msg`.
Envelope whitespace is normalized. The report includes raw websocket frame
hashes, feed SHA-256, receipt times, counts and missing topics. Existing feed
files are protected by exclusive creation. Endpoint identity and source status
are operator declarations; transport alone cannot prove their origin.

## Synthetic reconnect fixture

The mock server uses port 9091 and starts no ROS process. Its poses and clock
values are **SIMULATED test data**, unrelated to archive measurements or the
running Gazebo rover.

```bash
python3 scripts/t4_mock_rosbridge.py --port 9091 --duration 30 \
  --disconnect-after 5 --offline-for 3 \
  --report test-results/t4-mock.json
```

The outage timer starts at the first supported subscription. The server closes
existing clients and its listener, refuses connections during the gap, then
opens the same port. New connections must subscribe again. The report records
the wall-clock event timeline, received operations, and per-connection topic
publish counts with first/last times. UE stale transitions and backoff intervals
must be observed separately in UE.

Supported topics are `/rover_1/odom`, `/tf`, `/tf_static`, `/clock` and
`/redline/mission/clock`. Odometry has parent `rover_1/odom`, child
`rover_1/base_link`, position `(1,2,3)` metres and ROS yaw +90 degrees. TF supplies
identity `map → rover_1/odom`. The mission-clock fixture uses a distinct
`{clock:{sec,nanosec}}` payload offset by 3600 seconds; it does not establish the
future scenario-player message type. The repo currently has no dedicated
mission-clock message definition.

`/t4/echo` returns `service_response`, the same request `id`, `result=true`, and
`values={"echo":<args>}`. Other service names return `result=false`.
`advertise`, `unadvertise` and client `publish` operations are recorded without
forwarding to ROS. Unsupported operations return an error status.

## Observed checks and limits

`python3 -m unittest discover -s scripts/tests -p test_t4_rosbridge_tools.py -v`
passed **2 tests**, covering:

- Capture preserves message values, starts playback time at zero, records
  increasing receipt times and hashes, sends only subscribe/unsubscribe, and
  rejects overwriting evidence.
- The fixture closes the listener, refuses a connection during the outage,
  reopens, requires a new subscription, publishes the expected TF, and preserves
  the service request identity and echo arguments.

The tests use ephemeral loopback ports and synthetic values. Output and command
exit status are in `test-results/t4-support-tests.txt` and
`test-results/t4-support-tests.json`. `bash -n scripts/t4_rosbridge.sh` and both
Python CLI `--help` invocations also exited 0.

Testing exposed a shutdown cycle in Ubuntu's websockets 10.4 with Python 3.12:
the library awaits the underlying listener's closure before closing its clients,
while the listener also waits for clients. The fixture closes its tracked clients
explicitly, then awaits listener closure; the reconnect test verifies this path.

Pending integration evidence: an actual rosbridge session on port 9090, Windows
localhost forwarding, a captured live Gazebo feed, and UE coordinate/stale/
resubscription acceptance. This document marks no milestone complete.
