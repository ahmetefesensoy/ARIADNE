import pytest
from redline_core.campaign import Campaign, campaign_tasks


def command(c, cmd="START", **kw):
    args = dict(request_id=f"request-{c.revision}", command=cmd, target=c.task.target_id,
                revision=c.revision, position=c.task.xy, age_s=0.)
    args.update(kw)
    fresh = c.validate_command(**args)
    if fresh:
        c.accept(args["request_id"], cmd, args["target"], args["revision"])
    return args


def test_receipt_is_not_completion_and_failure_preserves_task():
    c = Campaign()
    command(c)
    assert c.index == 0 and not c.completed
    c.feedback("PREPARING", .2)
    c.finish(success=False, reason="sensor unavailable")
    assert c.index == 0 and c.state == "failed" and not c.completed
    command(c)
    c.finish(success=True)
    assert c.task.id == "scout"


@pytest.mark.parametrize("override", [dict(age_s=3), dict(age_s=float("nan")),
                                      dict(position=(0, 0)), dict(position=None),
                                      dict(revision=99), dict(target="WRONG")])
def test_fresh_position_target_and_revision_required(override):
    with pytest.raises(ValueError): command(Campaign(), **override)


def test_duplicate_request_cannot_repeat_or_change_intent():
    c = Campaign(); args = command(c)
    assert not c.validate_command(**args)
    with pytest.raises(ValueError): c.validate_command(**{**args, "command": "CANCEL"})


def test_no_result_can_skip_the_science_or_decision_chain():
    c = Campaign(); command(c); c.finish(success=True)
    command(c)
    with pytest.raises(ValueError, match="evidence"): c.finish(success=True)
    c.finish(success=True, evidence=["ev-scout-1"])
    with pytest.raises(ValueError): command(c)
    command(c, "CHOOSE_HOLLOW"); c.decide("CHOOSE_HOLLOW")
    assert c.task.target_id == "BXW_HOLLOW_B"
    command(c)
    with pytest.raises(ValueError): c.finish(success=True, products=["collect-photo"])
    c.finish(success=True, products=["collect-photo"], samples=["smp-BXW-1"])
    assert c.task.kind == "xrf" and c.sample_ids == ["smp-BXW-1"]


def test_full_campaign_requires_products_samples_and_explicit_assessment():
    c = Campaign()
    while not c.done:
        cmd = {"decision": "CHOOSE_RIDGE", "assessment": "NEED_MORE_DATA"}.get(c.task.kind, "START")
        command(c, cmd)
        if c.task.kind in ("decision", "assessment"):
            c.decide(cmd)
        else:
            c.finish(success=True, products=[f"sim-{c.task.id}"], evidence=[f"ev-{c.task.id}"],
                     samples=["smp-BXW-1"])
    assert len(c.completed) == 12 and c.state == "complete"
    assert c.decisions[-1]["chosen"] == "NEED_MORE_DATA"
    with pytest.raises(ValueError): command(c)


def test_task_definitions_are_same_eva_with_distinct_room_and_field_coordinates():
    tasks = campaign_tasks()
    assert len({t.id for t in tasks}) == 12
    assert tasks[3].xy != tasks[0].xy != tasks[9].xy
    assert {t.actor for t in tasks} == {"EV1", "rover_1", "scout_1"}
    with pytest.raises(ValueError): campaign_tasks("invalid")


def test_collection_requires_reach_distance_and_feedback_cannot_rewind():
    c=Campaign();c.index=3
    # A player standing beside the rock is within reach; 1.2 m made E look broken in play.
    near=Campaign();near.index=3
    command(near,position=(near.task.xy[0]+2.,near.task.xy[1]))
    with pytest.raises(ValueError,match="2.5 m"):
        command(c,position=(c.task.xy[0]+3.,c.task.xy[1]))
    command(c);c.feedback("ACQUIRING",.6);c.feedback("LATE_OLD_PACKET",.2)
    assert c.progress==.6 and c.index==3


def test_registered_long_field_targets_replace_tutorial_coordinates():
    c=Campaign({"BXW_RIDGE_A":(570.,-454.),"BXW_HOLLOW_B":(590.,-438.)})
    c.index=3
    assert c.task.xy==(570.,-454.)
    with pytest.raises(ValueError):command(c,position=(306.,-454.))
    command(c);c.finish(success=True,products=["collect"],samples=["smp-1"])
    assert c.task.xy==(570.,-454.)
    with pytest.raises(ValueError):Campaign({"BXW_RIDGE_A":(float("nan"),0.)})


@pytest.mark.parametrize("index", [6, 7, 8])
def test_rover_commands_work_remotely_but_require_fresh_crew_and_current_intent(index):
    c = Campaign()
    c.index = index
    command(c, position=(285.1, -468.))
    assert c.state == "pending" and c.index == index
    for override in (dict(age_s=3), dict(position=None), dict(position=(float("nan"), 0)),
                     dict(target="WRONG"), dict(revision=99)):
        other = Campaign()
        other.index = index
        with pytest.raises(ValueError):
            command(other, position=override.get("position", (285.1, -468.)),
                    **{k: v for k, v in override.items() if k != "position"})


@pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5, 9, 10, 11])
def test_human_interaction_and_pre_egress_scout_remain_local(index):
    c = Campaign()
    c.index = index
    cmd = {"decision": "CHOOSE_RIDGE", "assessment": "NEED_MORE_DATA"}.get(c.task.kind, "START")
    with pytest.raises(ValueError, match="yaklaş"):
        command(c, cmd, position=(c.task.xy[0] + 100., c.task.xy[1]))


def test_task_presentation_unlocks_sequentially_and_arrival_never_completes_work():
    c = Campaign()
    far = c.snapshot((0., 0.), 0.)
    assert far["task"]["presentation"]["state"] == "active"
    assert far["task"]["presentation"]["blocked_reason"] == "approach_site"
    assert all(t["presentation"]["state"] == "locked" for t in far["tasks"][1:])
    arrived = c.snapshot(c.task.xy, 0.)
    assert arrived["task"]["presentation"]["enabled"]
    assert arrived["task"]["presentation"]["arrived"]
    assert c.index == 0 and not c.completed
    command(c)
    running = c.snapshot(c.task.xy, 0.)
    assert not running["task"]["presentation"]["enabled"]
    assert running["task"]["presentation"]["blocked_reason"] == "operation_running"
    c.finish(success=False)
    assert c.snapshot(c.task.xy, 0.)["task"]["presentation"]["enabled"]
    command(c)
    c.finish(success=True)
    next_task = c.snapshot(c.task.xy, 0.)
    assert next_task["tasks"][0]["presentation"]["state"] == "complete"
    assert next_task["tasks"][1]["presentation"]["state"] == "active"
    assert next_task["tasks"][2]["presentation"]["state"] == "locked"
    stale = c.snapshot(c.task.xy, 3.)
    assert stale["task"]["presentation"]["distance_m"] is None
    assert stale["task"]["presentation"]["blocked_reason"] == "crew_pose_stale"


def test_remote_task_presentation_preserves_field_target_and_action_authority():
    locations = {"BXW_RIDGE_A": (570., -454.), "BXW_HOLLOW_B": (590., -438.)}
    c = Campaign(locations)
    c.index = 6
    view = c.snapshot((285.1, -468.), 0.)["task"]["presentation"]
    assert view["enabled"] and view["location_ready"] and not view["arrived"]
    assert view["interaction_mode"] == "remote" and not view["requires_proximity"]
    assert view["site_xy_m"] == [570., -454.]
    assert view["endpoint"] == "/rover_1/remote_libs" and view["action"] == "RemoteLibs"
    assert view["navigation_endpoint"] == "/rover_1/navigate_to_pose"
    assert view["command_endpoint"] == "/redline/campaign/command"
    unknown = c.snapshot()["task"]["presentation"]
    assert not unknown["crew_pose_fresh"] and not unknown["enabled"]
