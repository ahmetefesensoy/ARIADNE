# T4 independent implementation review

Read-only implementation review on 2026-11-14. No graph, goal, editor, build or
test was launched by the reviewer during this review. Reviewed the bridge C++,
Automation tests, `scripts/build-t4.ps1`, terrain fixture, and current T3 launch
files and local evidence.

The latest observed Automation report, created at `2026.11.14-13.04.27`, has
**6 succeeded, 0 warnings, 0 failed** in `test-results/t4-automation/index.json`.
The initially observed invalid subsystem Outer and float-PI test errors were
corrected during review: tests now use a `UGameInstance` Outer and
`UE_DOUBLE_PI/2`. The coordinate conversion formula was already correct.

## Remaining reliability fix

**P1 — request transient-local QoS explicitly for `/tf_static`.**

`RedlineBridgeSubsystem.cpp`, `SendSubscription`, currently emits no `qos` field.
The installed rosbridge 2.7.1
`rosbridge_library/internal/subscribers.py`, `_get_default_qos_profile`, selects
volatile durability when no publisher is discovered at the first subscription;
the manager fixes the profile at first registration. Starting UE/rosbridge
before localization can therefore lose a one-time static transform. The actor
correctly refuses odometry without `map → rover_1/odom`, so the visible result is
a rover that never starts updating despite fresh odometry.

Emit this verified installed-protocol option for `/tf_static` and retain it when
restoring subscriptions:

```json
{"qos":{"history":"keep_last","depth":1,"reliability":"reliable","durability":"transient_local"}}
```

The field names and values were checked against installed
`rosbridge_library/internal/qos_extraction.py`. The mocked server cannot verify
DDS durability; use a graph startup ordering check for that behavior.

## Acceptance evidence still needed

**Actual terrain collision traces.** At review time no
`test-results/t4-terrain-import.json` existed. The fixture's dimensions check is
useful for centimetre scale, but the square 250 m tiles do not prove horizontal
axis orientation. The three actual complex line traces must hit and meet the
0.1 m criterion. `break_hit_result` location index 4 and the metre/cm comparison
are consistent with the intended trace calculation. No terrain scale or
orientation failure is asserted without the trace result.

**Offline replay through the actor.** The current six Automation tests do not
exercise `StartOfflineFeed` or an actual rover actor. The capture must include
`/tf_static` in addition to `/rover_1/odom` and `/clock`; odometry uses the odom
frame and cannot be displayed in map coordinates without the static transform.
Verify that the first time-zero static transform reaches the actor: playback
can begin in subsystem initialization, while actor subscriptions are added in
`BeginPlay`. If playback consumes that latched record earlier, defer playback
until consumers are ready or retain/re-deliver static transforms.

**Cached terrain import provenance.** The fixture reuses any mesh already at its
asset path but reports the hash of the current FBX. A new source FBX with equal
extents could therefore be attributed to an old UAsset. On source changes,
reimport explicitly or verify stored imported-source hashes before reuse. On a
fresh first import this is not evidence of a mismatch.

## Frame, ownership and lifetime review

The actor composes the ROS `map → rover_1/odom` transform with odom position and
orientation before converting to centimetres and UE handedness. It rejects an
unexpected child/parent frame, absent transform, or excessive dynamic-TF skew,
and clears cached TF on disconnect. Its presentation component has collision
and physics disabled. No second robot physics/control authority was found.

Socket callbacks capture a weak UObject and generation, transfer to the game
thread, and reject callbacks from previous generations. Deinitialization removes
the ticker, clears socket delegates, fails pending requests and clears topic
listeners. Commands are not replayed on reconnect; the service reply is described
as acceptance rather than action completion. No blocking lifetime defect was
found in these inspected paths.

The planar T3 EKF intentionally estimates zero odom Z; its static spawn transform
supplies map altitude. Compare UE against the composed ROS estimate, and identify
that estimate separately from Gazebo world truth on uneven terrain.

## Root-owned persistent runtime recommendation

The successful observed T3 RViz run is
`test-results/t3-runtime-rSbG87au/result.json`. Its workspace was
`/home/ahmetefesensoy/.cache/redline/ros/ws-1749a5d0a400754b-z1wesfxy`; its world
`bxw.sdf` SHA-256 is
`6b6a5539160288154e83e7cd054882aa3b1447bea017e915e086970a1fcb73d8`.
Its reported goal error was 0.4913 m and action status 4. This is prior T3
evidence, not a T4 run.

`t3_supervisor.py` shuts down simulation and navigation immediately after its
bounded verifier completes. For a persistent T4 observation, the root operator
should source Jazzy plus the explicitly selected built overlay, set domain 77
and partition `redline`, then own separate long-running processes for:

- `redline_bringup/simulation.launch.py`, with the verified existing generated
  world or a newly generated equivalent.
- `redline_navigation/navigation.launch.py`, using the verified terrain cache
  `~/.cache/redline/t3/terrain-bxw-v2/nav_map.yaml` and manifest spawn
  `x=145`, `y=-289`, `z=-3598.4697875976562`, `yaw=4.71238898038469`.
- `scripts/t4_rosbridge.sh <built-workspace>` on port 9090.

Root should coordinate any new Nav2/RViz goal and cleanup of these processes.
The reviewer made no launch or command dispatch. Regenerate
`.agents/ue-project-context.md` before handoff; it still says no project exists.
