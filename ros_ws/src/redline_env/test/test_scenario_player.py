"""scenario_player: scheduled events carry the canonical D015 payload on PET."""
import time

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock

from redline_core.scenario import ScenarioEvent, parse_event
from redline_env.scenario_player import EVENT_QOS, EVENT_TOPIC, STATE_QOS, ScenarioPlayerNode
from redline_msgs.msg import Alert

SCENARIO = """id: T
site: TST
seed: 1
start: {historical_utc: '2024-05-20T00:00:00Z'}
crew: [EV1, EV2]
events:
  - {t_min: 1.0, type: SUIT_LEAK, params: {crew_id: EV2, k_leak: 3.0}}
"""


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def test_a_scheduled_event_is_published_once_with_a_parseable_payload(ros, tmp_path):
    (tmp_path / "s.yaml").write_text(SCENARIO)
    node = ScenarioPlayerNode(parameter_overrides=[Parameter("scenario_file", value=str(tmp_path / "s.yaml")),
                                                   Parameter("auto_start", value=False)])
    probe = rclpy.create_node("probe")
    events = []
    probe.create_subscription(Alert, EVENT_TOPIC, events.append, EVENT_QOS)
    clock = probe.create_publisher(Clock, "/redline/mission/clock", STATE_QOS)
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(probe)

    def spin(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=0.01)

    try:
        spin(0.5)
        for pet in (30, 59, 61, 90):
            message = Clock()
            message.clock.sec = pet
            clock.publish(message)
            spin(0.2)
        assert [e.code for e in events] == ["SUIT_LEAK"]
        assert parse_event(events[0].text) == ScenarioEvent(1.0, "SUIT_LEAK", {"crew_id": "EV2", "k_leak": 3.0})
    finally:
        executor.shutdown()
        node.destroy_node()
        probe.destroy_node()
