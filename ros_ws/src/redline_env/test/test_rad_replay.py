"""rad_replay over real DDS with a SIMULATED RDR excerpt: PET→UTC, stepwise dose, alarm PET."""
import math
import time
from datetime import datetime, timedelta, timezone

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock

from redline_data.rad import write_rad_table
from redline_env.rad_replay import CLOCK_TOPIC, DOSE_TOPIC, STATE_QOS, RadReplayNode
from redline_msgs.msg import DoseRate

START = datetime(2024, 5, 20, 0, 0, 0, tzinfo=timezone.utc)
JUMP = START + timedelta(hours=8)  # dose rises from 5 to 20 µGy/h here (SIMULATED test data)


def rdr_text(sol=9999):
    lines = ["[FILE]", f"START_SOL={sol}", ""]
    for k in range(0, 10 * 6 * 2, 2):  # every 10 min for 10 h, dose blocks on even NN
        t = START + timedelta(minutes=5 * k)
        doy = t.timetuple().tm_yday
        value = 20.0 if t >= JUMP else 5.0
        lines += [f"[OBSERVATION: {k:02d}]", f'START_OBS_MARS="{sol} 0:00:00"',
                  f'START_OBS_UTC="{t.year}-{doy:03d} {t:%H:%M:%S}"', "",
                  f"[DOSIMETRY_TOTAL_DOSE_B: {k:02d}]", "", f"{value + 1.0}", "",
                  f"[DOSIMETRY_TOTAL_DOSE_E: {k:02d}]", "", f"{value}", ""]
    return "\n".join(lines) + "\n"


@pytest.fixture
def files(tmp_path):
    rdr = tmp_path / "RAD_TEST.TXT"
    rdr.write_text(rdr_text(), encoding="ascii")
    env = tmp_path / "env"
    write_rad_table(rdr, env / "rad_9999.csv", source_url="simulated://test")
    scenario = tmp_path / "s.yaml"
    scenario.write_text("id: TEST\nsite: TST\nseed: 1\ntime_scale: 1\n"
                        "start: {historical_utc: '2024-05-20T07:00:00Z', pet_min: 0}\n"
                        "crew: [EV1]\nreplay: {rad: {sols: [9999], detector: E}}\n")
    return scenario, env


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def test_alarm_arrives_at_the_pet_of_the_first_high_reading(ros, files):
    scenario, env = files
    node = RadReplayNode(parameter_overrides=[Parameter("scenario_file", value=str(scenario)),
                                              Parameter("env_dir", value=str(env))])
    probe = rclpy.create_node("probe")
    clock = probe.create_publisher(Clock, CLOCK_TOPIC, STATE_QOS)
    doses = []
    probe.create_subscription(DoseRate, DOSE_TOPIC, doses.append, STATE_QOS)
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(probe)

    def at(pet):
        message = Clock()
        message.clock.sec, message.clock.nanosec = int(pet), int((pet - int(pet)) * 1e9)
        count = len(doses)
        clock.publish(message)
        end = time.monotonic() + 5
        while time.monotonic() < end and len(doses) == count:
            executor.spin_once(timeout_sec=0.02)
        return doses[-1]

    try:
        end = time.monotonic() + 3
        while time.monotonic() < end and node.count_publishers(CLOCK_TOPIC) == 0:
            executor.spin_once(timeout_sec=0.02)
        before = at(59 * 60.0)  # 07:59 UTC
        assert not before.alert and before.dose_rate_e_ugy_h == pytest.approx(5.0)
        assert before.background_e_ugy_h == pytest.approx(5.0) and before.dose_rate_b_ugy_h == pytest.approx(6.0)
        assert before.alert_detector == "E" and before.source_sol == 9999
        held = at(59 * 60.0 + 59.0)  # still the 07:50 reading: stepwise, no interpolation
        assert held.dose_rate_e_ugy_h == pytest.approx(5.0)
        after = at(60 * 60.0)  # 08:00 UTC: the 20 µGy/h reading starts
        assert after.alert and after.dose_rate_e_ugy_h == pytest.approx(20.0)
        assert after.historical_utc.sec == int(JUMP.timestamp())
        assert node.alert_pet_s == pytest.approx(3600.0)
        assert math.isfinite(after.background_e_ugy_h)
    finally:
        executor.shutdown()
        node.destroy_node()
        probe.destroy_node()
