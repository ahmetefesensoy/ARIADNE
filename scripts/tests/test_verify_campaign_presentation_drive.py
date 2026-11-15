"""Admission guards for a diagnostic that may submit exactly one simulation goal."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import importlib.util
import json
import math
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "campaign_presentation_drive", Path(__file__).resolve().parents[1]/"verify_campaign_presentation_drive.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def idle():
    return {"schema": "redline.campaign.v1", "state": "ready", "task_index": 0,
            "revision": 0, "task": {"id": "briefing"}, "operation_id": ""}


@pytest.mark.parametrize("replacement", [
    {"state": "running"}, {"task_index": 1}, {"revision": 1},
    {"task": {"id": "scout"}}, {"operation_id": "real-user-operation"},
    {"task_index": False}, {"revision": False}, {"task": None},
])
def test_diagnostic_cannot_enter_an_active_or_malformed_campaign(replacement):
    state = idle()
    assert probe.untouched_briefing(state)
    state.update(replacement)
    assert not probe.untouched_briefing(state)


def manifest():
    return {"frame": "map", "units": "m", "goal": {
        "map_x_m": -33., "map_y_m": -382., "ground_z_m": -3596., "yaw_rad": 0.}}


def test_goal_keeps_staged_map_units_and_negative_mars_elevation_without_mutation():
    source = manifest()
    original = deepcopy(source)
    assert probe.staged_goal(source) == (-33., -382., -3596., 0.)
    assert source == original


@pytest.mark.parametrize("field,value", [
    ("map_x_m", math.nan), ("map_y_m", math.inf), ("ground_z_m", True),
    ("yaw_rad", "0"), ("map_x_m", 1e9),
])
def test_invalid_staged_goal_is_rejected_before_any_ros_initialization(field, value):
    source = manifest()
    source["goal"][field] = value
    with pytest.raises(ValueError):
        probe.staged_goal(source)


@pytest.mark.parametrize("field,value", [("frame", "odom"), ("units", "cm")])
def test_unaligned_or_cm_manifest_cannot_become_a_map_goal(field, value):
    source = manifest()
    source[field] = value
    with pytest.raises(ValueError):
        probe.staged_goal(source)


def test_default_guard_still_rejects_absent_status():
    assert not probe.status_admits_goal(received=False, age_s=math.inf, busy=False,
                                       listening_s=100, expected_publisher=True)


def test_owned_guard_admits_only_absence_after_reliable_single_publisher_observation():
    arguments=dict(received=False, age_s=math.inf, busy=False, owned_absence=True,
                   listening_s=2.1, expected_publisher=True)
    assert probe.status_admits_goal(**arguments)
    for replacement in ({'listening_s':1.99},{'listening_s':math.nan},
                        {'expected_publisher':False},{'busy':True},{'owned_absence':False}):
        assert not probe.status_admits_goal(**(arguments|replacement))


@pytest.mark.parametrize('age,busy,expected',[(.5,False,True),(.5,True,False),
                                           (2.,False,False),(math.inf,False,False),(-.1,False,False)])
def test_owned_mode_never_overrides_received_busy_or_stale_state(age,busy,expected):
    assert probe.status_admits_goal(received=True, age_s=age, busy=busy,
        owned_absence=True,listening_s=10,expected_publisher=True) is expected


def owner_fixture(tmp_path):
    session=tmp_path/'campaign-test';session.mkdir();proc=tmp_path/'proc';proc.mkdir()
    owner=proc/'321';owner.mkdir();robot=proc/'654';robot.mkdir()
    receipt={'schema':'redline.campaign.owned-first-goal.v1','domain_id':185,
             'campaign_run_id':'test-run-1','no_commands_sent':True,'physics_authority':'Gazebo',
             'supervisor_pid':321,'robot_supervisor_pid':654,'supervisor_start_ticks':'43210',
             'gz_partition':'redline-campaign-campaign-test','evidence_path':str(session),
             'created_at_utc':datetime.now(timezone.utc).isoformat()}
    fields=['S']+['0']*18+['43210']+['0']*6
    (owner/'stat').write_text('321 (bash with spaces) '+' '.join(fields))
    (owner/'cmdline').write_bytes(b'bash\0/work/scripts/run-campaign-backend.sh\0/workspace\0')
    (robot/'cmdline').write_bytes(b'/usr/bin/python3\0/work/scripts/t3_supervisor.py\0')
    (robot/'environ').write_bytes(b'ROS_DOMAIN_ID=185\0GZ_PARTITION=redline-campaign-campaign-test\0')
    (session/'supervisor.pid').write_text('321\n');(session/'process-groups.txt').write_text('654\n655\n')
    path=session/'owned-first-goal.json';path.write_text(json.dumps(receipt))
    return path,receipt,proc


def test_receipt_binds_live_owner_and_cannot_be_reused(tmp_path):
    path,receipt,proc=owner_fixture(tmp_path)
    assert probe.owned_receipt_identity(receipt,185,'test-run-1')
    assert probe.validate_owned_processes(path,receipt,185,proc_root=proc)
    (path.parent/'first-goal.claim.json').write_text('{}')
    with pytest.raises(ValueError,match='consumed'):
        probe.validate_owned_processes(path,receipt,185,proc_root=proc)


@pytest.mark.parametrize('key,value',[('domain_id',183),('domain_id',True),
    ('campaign_run_id','other-run'),('no_commands_sent',False),('physics_authority','Unreal'),
    ('supervisor_pid',True),('gz_partition','another-session')])
def test_wrong_identity_never_admits_owned_mode(tmp_path,key,value):
    _,receipt,_=owner_fixture(tmp_path);receipt[key]=value
    with pytest.raises(ValueError):probe.owned_receipt_identity(receipt,185,'test-run-1')


@pytest.mark.parametrize('replacement',['pid_reused','domain_changed','partition_changed','expired','naive_time','wrong_directory'])
def test_live_owner_verification_rejects_changed_process_or_receipt(tmp_path,replacement):
    path,receipt,proc=owner_fixture(tmp_path)
    if replacement=='pid_reused':
        stat=proc/'321/stat';stat.write_text(stat.read_text().replace('43210','99999'))
    elif replacement=='domain_changed':(proc/'654/environ').write_bytes(b'ROS_DOMAIN_ID=184\0GZ_PARTITION=redline-campaign-campaign-test\0')
    elif replacement=='partition_changed':(proc/'654/environ').write_bytes(b'ROS_DOMAIN_ID=185\0GZ_PARTITION=other\0')
    elif replacement=='expired':receipt['created_at_utc']=(datetime.now(timezone.utc)-timedelta(seconds=901)).isoformat()
    elif replacement=='naive_time':receipt['created_at_utc']=datetime.now().isoformat()
    elif replacement=='wrong_directory':receipt['evidence_path']=str(tmp_path)
    with pytest.raises(ValueError):probe.validate_owned_processes(path,receipt,185,proc_root=proc)
