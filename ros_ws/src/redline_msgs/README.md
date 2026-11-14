# redline_msgs

Shared interfaces implemented from the final `docs/proje.md`, section 5.
This package contains 22 messages, 5 services, and 11 actions. It does not
implement a mission manager, robot driver, planner, action server, or UI.

All field types and names follow the specification. Each action Result also
declares SUCCEEDED=0, PARTIAL=1, CANCELED=2, FAILED=3 and REJECTED=4, as required
by the prose preceding section 5.3. These application outcomes are separate
from the ROS action protocol's GoalStatus values.

`CollectSample` is named in some research prose but has no section 5 schema;
it is not invented here. Sample operations are described by the defined
SampleRecord, Drill and CacheSample contracts. Later schema changes require
a record in `docs/DECISIONS.md`.

The FieldTile schema retains `uint8 nodata_byte` exactly as specified. It
cannot represent every possible 16-bit nodata value. The 8/16-bit image
encoding contract needs clarification before a producer is implemented.
Generated ROS classes serialize data; they do not enforce planning semantics,
freshness, numeric ranges, or PNG decoding rules.

## Build and test

Use the ROS Jazzy underlay and the repository's bootstrap/check scripts.
For manual checks from `ros_ws` in WSL:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select redline_msgs --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/local_setup.bash
colcon test --packages-select redline_msgs --event-handlers console_direct+
colcon test-result --verbose
```

The pytest suite exercises generated Python type support and CDR serialization,
including nested messages, binary PNG bytes, NaN raster values, provenance,
separate sample origin/analysis points, independent measurement/publication
timestamps, and every service/action payload. It requires no running robot or
DDS graph and makes no claim about node behavior or Gazebo/Unreal integration.

The package maintainer address is an explicit non-deliverable placeholder.
No licence for new project code has been selected; the package uses the
explicit pending identifier `LicenseRef-Project-Pending`. Third-party research/skill
licences elsewhere in the repository remain unchanged.
