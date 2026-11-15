"""env_server: SPICE-table interpolation on mission time (synthetic table, SIMULATED)."""
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone

import pytest
import rclpy
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock

from redline_env.env_server import EnvServerNode


@pytest.fixture
def files(tmp_path):
    start = datetime(2024, 5, 20, 0, 0, tzinfo=timezone.utc)
    rows = ["utc,sun_az_deg,sun_el_deg,earth_light_time_s"]
    for k in range(0, 121):  # every minute for 2 h; azimuth crosses 360 → 0
        t = start + timedelta(minutes=k)
        rows.append(f"{t:%Y-%m-%dT%H:%M:%SZ},{(350.0 + k * 0.2) % 360:.4f},{10.0 + k * 0.1:.4f},950.000")
    table = tmp_path / "sun.csv"
    table.write_text("\n".join(rows) + "\n", encoding="utf-8")
    sidecar = {"site": {"lon_east_deg": 137.37}, "csv_sha256": hashlib.sha256(table.read_bytes()).hexdigest()}
    (tmp_path / "sun.json").write_text(json.dumps(sidecar))
    scenario = tmp_path / "s.yaml"
    scenario.write_text("id: T\nsite: TST\nseed: 1\ntime_scale: 1\nstart: {historical_utc: '2024-05-20T00:30:00Z', "
                        "pet_min: 0}\ncrew: [EV1]\n")
    return table, scenario


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.try_shutdown()


def test_state_interpolates_the_table_and_wraps_azimuth(ros, files):
    table, scenario = files
    node = EnvServerNode(parameter_overrides=[Parameter("sun_table", value=str(table)),
                                              Parameter("scenario_file", value=str(scenario))])
    try:
        assert node.state() is None  # no mission clock yet
        clock = Clock()
        clock.clock.sec, clock.clock.nanosec = 30, 0  # PET 30 s → 00:30:30 UTC → table minute 30.5
        node._on_clock(clock)
        state = node.state()
        assert state.sun_el_deg == pytest.approx(10.0 + 30.5 * 0.1, abs=1e-6)
        assert state.sun_az_deg == pytest.approx((350.0 + 30.5 * 0.2) % 360, abs=1e-3)  # 356.1°, wrap-safe
        assert state.earth_light_time_s == pytest.approx(950.0)
        assert state.mission_sol == 1 and len(state.lmst) == 8 and state.provenance.status == 1
        assert math.isnan(state.pressure_pa)
        clock.clock.sec = 3600  # 01:30 UTC: past the azimuth wrap at minute 50
        node._on_clock(clock)
        assert node.state().sun_az_deg == pytest.approx((350.0 + 90 * 0.2) % 360, abs=1e-3)
        clock.clock.sec = 3 * 3600  # outside the table: no extrapolation
        node._on_clock(clock)
        assert math.isnan(node.state().sun_el_deg)
    finally:
        node.destroy_node()
