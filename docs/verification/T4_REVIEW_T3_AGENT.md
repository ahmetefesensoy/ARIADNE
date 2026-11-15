# Independent T4 source review

Reviewed `unreal/Redline/Plugins/RedlineBridge/Source` on 14 November 2026 for
the technical cube, ROS pose, coordinate and terrain acceptance scope. This was
a source and existing-evidence review. No Unreal build, UI operation, ROS graph
or runtime was started, and no T4 source file was changed.

One concrete P2 defect was found in `RedlineBridgeSubsystem.cpp`, in `Tick`'s
expired-service loop. It collects expired IDs, then calls `FindChecked` and the
user callback for each ID. With two expired services, the first callback can
call `Disconnect`, whose `FailPending` clears the remaining entries. The next
`FindChecked` then asserts. Move expired records into a local collection before
invoking callbacks, or check membership again before each removal. This affects
service timeout and connection lifecycle behavior; it does not invalidate the
presentation cube's coordinate result. The finding was sent to the integration
owner and T4 lead. It was established by following the concrete callback path,
without executing that failure case.

No other definite blocker was found in the reviewed acceptance path. Socket
delegates queue copied payloads onto the game thread, hold weak UObject
references, and fence callbacks by connection generation. Disconnect invalidates
freshness and pending service responses; reconnect restores subscriptions without
replaying commands. Odometry is validated before it marks the stream fresh.
Wall receipt time governs freshness independently of ROS physics and PET clocks.

The ROS-to-Unreal position and quaternion mapping matches spec section 4.2.
`ComposeRosPose` applies map-to-odom rotation and translation before the engine
conversion. The presentation actor disables collision and physics. The installed
rosbridge 2.7.1 subscriber implementation selects transient-local reliability and
durability when the discovered publishers require it, and creates a temporary
subscription to replay latched data to a newly added subscriber. No missing
`tf_static` replay defect was established for the coordinated T3-first startup.

The existing `test-results/t4-automation/index.json` reported the invalid
subsystem test Outer, float-PI coordinate expectations and reconnect failures.
The T4 lead was already editing those tests during this review; that older index
was not treated as evidence for the subsequent source state. T5/T6 parsers and
final UI were outside this review.
