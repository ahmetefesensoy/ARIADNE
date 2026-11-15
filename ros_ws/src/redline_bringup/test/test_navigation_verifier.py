"""RViz goal/status correlation tests; no nodes, simulator or ROS graph started."""

import importlib.util
from pathlib import Path

import pytest
from action_msgs.msg import GoalStatus, GoalStatusArray
from geometry_msgs.msg import PoseStamped


spec=importlib.util.spec_from_file_location('verify_navigation',Path(__file__).parents[1]/'scripts/verify_navigation.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
EXPECTED={'map_x_m':145.0,'map_y_m':-299.0,'ground_z_m':-3599.12939453125,'yaw_rad':0.0}
RVIZ={'node_name':'rviz_navigation','node_namespace':'/rover_1','publisher_gid':'12'*24}


def pose(stamp=12_000_000_000,x=145.0,y=-299.0,frame='map'):
    message=PoseStamped();message.header.frame_id=frame
    message.header.stamp.sec=stamp//1_000_000_000
    message.header.stamp.nanosec=stamp%1_000_000_000
    message.pose.position.x=x;message.pose.position.y=y;message.pose.orientation.w=1.0
    return message


def status(uuid_number=1,state=2,accepted_ns=12_010_000_000):
    entry=GoalStatus();entry.goal_info.goal_id.uuid=[uuid_number]*16
    entry.goal_info.stamp.sec=accepted_ns//1_000_000_000
    entry.goal_info.stamp.nanosec=accepted_ns%1_000_000_000
    entry.status=state
    array=GoalStatusArray();array.status_list=[entry]
    return array


def tracker():
    result=module.RvizGoalTracker(EXPECTED);result.arm(10_000_000_000)
    return result


def observed_value():
    return {'schema':'redline.t3.rviz-goal.v1','goal_topic':module.GOAL_TOPIC,
            'source_timestamp_ns':123,'publisher':dict(RVIZ),
            'pose':{'stamp_sec':12,'stamp_nanosec':3,'frame_id':'map',
                    'position':[145.0,-299.0,0.0],'orientation':[0.0,0.0,0.0,1.0]}}


def test_cpp_observer_payload_preserves_original_pose_stamp_and_dds_writer():
    message,publisher=module.decode_observed_goal(observed_value())
    assert module.stamp_ns(message.header.stamp)==12_000_000_003
    assert message.pose.position.x==145.0 and message.pose.position.y==-299.0
    assert publisher==RVIZ


@pytest.mark.parametrize('change',[
    lambda v:v.update(schema='unexpected'),
    lambda v:v.update(goal_topic='/unrelated_goal'),
    lambda v:v['publisher'].update(publisher_gid=''),
    lambda v:v['publisher'].update(publisher_gid='00'*16),
    lambda v:v['publisher'].update(publisher_gid='not hex'),
])
def test_unverifiable_observer_payload_is_rejected(change):
    value=observed_value();change(value)
    with pytest.raises(ValueError):module.decode_observed_goal(value)


def test_retained_success_and_late_old_uuid_never_count_as_fresh_goal_success():
    result=module.RvizGoalTracker(EXPECTED)
    result.receive_status(status(1,4,9_000_000_000));result.arm(10_000_000_000)
    result.receive_goal(pose(),RVIZ)
    result.receive_status(status(1,4,9_000_000_000))
    result.receive_status(status(2,4,8_000_000_000))  # retained UUID first seen after arming
    assert result.goal_uuid is None and result.status is None
    result.receive_status(status(3,2));result.receive_status(status(3,4))
    assert result.goal_uuid=='03'*16 and result.status==4 and result.error is None
    assert result.evidence()['baseline_uuids']==['01'*16]


def test_status_can_arrive_before_goal_callback_on_a_separate_topic():
    result=tracker();result.receive_status(status(7,4))
    assert result.goal_uuid is None
    result.receive_goal(pose(),RVIZ)
    assert result.goal_uuid=='07'*16 and result.status==4
    assert result.goal['ground_z_m']==EXPECTED['ground_z_m']
    assert result.publisher==RVIZ


def test_unarmed_old_unstamped_and_non_rviz_goals_are_ignored():
    result=module.RvizGoalTracker(EXPECTED)
    result.receive_goal(pose(),RVIZ);result.arm(10_000_000_000)
    result.receive_goal(pose(9_999_999_999),RVIZ)
    result.receive_goal(pose(0),RVIZ)
    result.receive_goal(pose(),{'node_name':'scripted_goal'})
    result.receive_goal(pose(),None)
    assert result.goal is None and result.error is None
    assert result.ignored['before_readiness']==1
    assert result.ignored['old_or_unstamped_pose']==2
    assert result.ignored['non_rviz_or_unresolved_publisher']==2


def test_duplicate_goal_does_not_restart_tracking_but_second_distinct_goal_fails():
    result=tracker();message=pose();result.receive_goal(message,RVIZ)
    result.receive_status(status(4,2));result.receive_goal(message,RVIZ)
    assert result.ignored['duplicate_pose']==1 and result.goal_uuid=='04'*16
    assert result.error is None
    result.receive_goal(pose(stamp=12_500_000_000,x=145.1),RVIZ)
    assert 'second distinct RViz goal' in result.error


@pytest.mark.parametrize('state',[5,6])
def test_canceled_or_aborted_action_is_a_reported_failure(state):
    result=tracker();result.receive_goal(pose(),RVIZ);result.receive_status(status(5,state))
    assert result.status==state and f'status {state}' in result.error
    assert result.evidence()['error']==result.error


def test_two_new_action_ids_fail_instead_of_accepting_unrelated_success():
    result=tracker();result.receive_goal(pose(),RVIZ)
    result.receive_status(status(1,2));result.receive_status(status(2,4))
    assert 'Multiple new Nav2 action UUIDs' in result.error


@pytest.mark.parametrize('message,expected_error',[
    (pose(x=147.0),'outside the controlled manifest target'),
    (pose(frame='rover_1/odom'),'expressed in map'),
    (pose(x=float('nan')),'non-finite'),
])
def test_wrong_or_unverifiable_rviz_target_is_rejected(message,expected_error):
    result=tracker();result.receive_goal(message,RVIZ)
    assert result.goal is None and expected_error in result.error


def test_goal_uses_clicked_xy_but_ground_height_only_from_nearby_manifest_target():
    result=tracker();message=pose(x=145.6,y=-298.6)
    message.pose.position.z=0.0  # RViz is a 2D goal; its Z is never ground truth.
    result.receive_goal(message,RVIZ)
    assert result.goal['map_x_m']==145.6 and result.goal['map_y_m']==-298.6
    assert result.goal['ground_z_m']==EXPECTED['ground_z_m']
    invalid=tracker();message.pose.orientation.w=0.0;invalid.receive_goal(message,RVIZ)
    assert 'quaternion is not normalized' in invalid.error


def test_zero_uuid_or_pre_goal_action_cannot_end_the_run():
    result=tracker();result.receive_goal(pose(),RVIZ)
    result.receive_status(status(0,4));result.receive_status(status(2,4,11_000_000_000))
    assert result.status is None and result.goal_uuid is None
