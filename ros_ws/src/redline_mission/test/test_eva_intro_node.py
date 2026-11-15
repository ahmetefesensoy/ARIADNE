"""Actual DDS/service progression; the client cannot set a mission phase."""
import time
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from redline_mission.mission_manager import MissionManagerNode, STATE_QOS
from redline_msgs.msg import CrewState, MissionState
from std_srvs.srv import Trigger


def test_real_advance_service_requires_fresh_nearby_ev1_and_clock_ack():
    rclpy.init()
    manager = MissionManagerNode(parameter_overrides=[
        Parameter('intro_enabled', value=True), Parameter('initial_phase', value='BRIEFING'),
        Parameter('intro_briefing_xy', value=[0., 0.]), Parameter('intro_station_xy', value=[16., 0.])])
    clock = Node('sim_clock')
    clock.declare_parameter('running', False)
    probe = Node('intro_probe')
    client = probe.create_client(Trigger, '/redline/mission/advance')
    pub = probe.create_publisher(CrewState, '/crew/EV1/state', STATE_QOS)
    executor = SingleThreadedExecutor()
    for node in (manager, clock, probe): executor.add_node(node)

    def until(predicate, timeout=6):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.02)
            if predicate(): return
        raise AssertionError('DDS/service condition not reached')

    def advance():
        f = client.call_async(Trigger.Request())
        until(f.done)
        return f.result()

    def pose(x):
        old = manager._ev1_receipt
        m = CrewState()
        m.crew_id = 'EV1'
        m.header.frame_id = 'map'
        m.pose.pose.orientation.w = 1.
        m.pose.pose.position.x = x
        pub.publish(m)
        until(lambda: manager._ev1_receipt != old)

    try:
        until(lambda: client.service_is_ready() and pub.get_subscription_count() > 0
              and manager._clock_control.services_are_ready())
        assert not advance().success  # no position
        pose(16.)
        assert not advance().success  # remote from briefing
        pose(0.)
        assert advance().success
        until(lambda: manager.phase == MissionState.TRAVERSE)
        assert clock.get_parameter('running').value is True
        assert not advance().success  # remote from station
        pose(16.)
        manager.sep_alert = True
        assert not advance().success  # SEP has priority over interaction
        manager.sep_alert = False
        assert advance().success and manager.phase == MissionState.STATION_SCIENCE
        assert advance().success and manager.phase == MissionState.RETURN
        assert not advance().success  # cannot finish away from shelter
        pose(0.)
        assert advance().success and manager.phase == MissionState.DEBRIEF
        assert not advance().success
        assert len(manager.transitions) == 4
    finally:
        executor.shutdown()
        for node in (probe, clock, manager): node.destroy_node()
        rclpy.try_shutdown()
