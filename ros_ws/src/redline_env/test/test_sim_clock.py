"""sim_clock node over real DDS: PET advances at the scale, scale changes at runtime."""
import time

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock

from redline_env.sim_clock import STATE_QOS, TOPIC, SimClockNode


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def collect(executor, received, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        executor.spin_once(timeout_sec=0.02)
    return received


def pet(message: Clock) -> float:
    return message.clock.sec + message.clock.nanosec * 1e-9


def test_pet_advances_at_the_configured_scale_and_changes_at_runtime(ros):
    node = SimClockNode(parameter_overrides=[Parameter("start_pet_s", value=100.0),
                                             Parameter("time_scale", value=10.0),
                                             Parameter("rate_hz", value=20.0)])
    probe = rclpy.create_node("probe")
    received = []
    probe.create_subscription(Clock, TOPIC, lambda m: received.append((time.monotonic(), pet(m))), STATE_QOS)
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(probe)
    try:
        collect(executor, received, 1.5)
        assert len(received) >= 10
        assert received[0][1] >= 100.0
        values = [v for _, v in received]
        assert values == sorted(values)
        (t0, p0), (t1, p1) = received[2], received[-1]
        assert (p1 - p0) / (t1 - t0) == pytest.approx(10.0, rel=0.1)

        assert node.set_parameters([Parameter("time_scale", value=1.0)])[0].successful
        received.clear()
        collect(executor, received, 1.2)
        (t0, p0), (t1, p1) = received[2], received[-1]
        assert (p1 - p0) / (t1 - t0) == pytest.approx(1.0, rel=0.1)

        assert not node.set_parameters([Parameter("time_scale", value=0.0)])[0].successful
        assert not node.set_parameters([Parameter("rate_hz", value=5.0)])[0].successful
    finally:
        executor.shutdown()
        node.destroy_node()
        probe.destroy_node()


def test_rejects_a_non_positive_rate(ros):
    with pytest.raises(ValueError):
        SimClockNode(parameter_overrides=[Parameter("rate_hz", value=0.0)])


def test_a_paused_clock_holds_pet_until_running_is_set(ros):
    node = SimClockNode(parameter_overrides=[Parameter("start_pet_s", value=50.0),
                                             Parameter("running", value=False)])
    try:
        before = node.pet()
        time.sleep(0.3)
        assert node.pet() == before == 50.0
        assert node.set_parameters([Parameter("running", value=True)])[0].successful
        time.sleep(0.3)
        assert node.pet() > 50.2
        assert node.set_parameters([Parameter("running", value=False)])[0].successful
        held = node.pet()
        time.sleep(0.2)
        assert node.pet() == held
    finally:
        node.destroy_node()
