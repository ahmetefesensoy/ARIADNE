# T3 RViz goal evidence

The Jazzy `rclpy` callback metadata observed on 14 November 2026 is a dictionary
with `source_timestamp`, `received_timestamp`, `publication_sequence_number` and
`reception_sequence_number`. It contains no `publisher_gid`. Reading that value
as either an attribute or dictionary key cannot establish the original writer.

`redline_bringup/rviz_goal_observer` uses the original `PoseStamped` subscription's
`rclcpp::MessageInfo::get_rmw_message_info().publisher_gid`. It matches that GID
against discovered endpoints and accepts the matched `rviz_navigation` or
`rviz2` writer. Unresolved, zero and unrelated writers emit no evidence. It
publishes the original pose, timestamp, matched node and GID as JSON on
`/redline/t3/rviz_goal_evidence`; it publishes no goal or velocity command.

The managed verifier requires one observer publisher, checks the evidence
schema, pose and target, then correlates a fresh Nav2 UUID after its readiness
baseline. Status 4, estimated and independently measured travel, target error,
and terrain height checks remain required. This is a controlled acceptance run
with one goal source. Timestamp correlation does not prove which action request
caused success when unrelated clients submit simultaneous goals. The height
check compares model geometry with manifest elevation; it is not contact-sensor
evidence.

Fresh snapshot `/home/ahmetefesensoy/.cache/redline/ros/ws-1749a5d0a400754b-z1wesfxy`
passed `bash scripts/build-t3.sh`: 63 reported test records, including 55 actual
test cases and 8 CTest wrappers, with no failures or skips. The copied build
evidence is `test-results/t3-build-njksBciX`. The observer integration test runs
its actual binary on isolated ROS domain 79. It rejects an unrelated publisher
on the same test topic, preserves the accepted pose and real GID, verifies that
no goal publisher was added, and shuts the observer down within a deadline.

The actual UI run `t3-runtime-rSbG87au` completed with a new Nav2 UUID at status
4. The rover moved 9.4963 m in Gazebo and stopped 0.4921 m from the clicked goal;
its manifest elevation residual was 0.00524 m. `T3_RVIZ_ACCEPTANCE.json` records
the original RViz publisher GID, timestamps, metrics and artifact hashes.

That run's observer `ros2 run` wrapper required the supervisor's bounded SIGKILL
fallback. The supervisor now invokes the installed observer binary directly.
An isolated lifecycle check using the same process-group ownership reached
readiness and exited 0 after SIGINT in 0.107 s without publishing a goal. Its
evidence is `test-results/t3-observer-cleanup-20261114/result.json`; this cleanup
check is separate from the successful navigation run.
