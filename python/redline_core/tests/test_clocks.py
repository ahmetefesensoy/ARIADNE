from datetime import datetime, timedelta, timezone
import math

import pytest

from redline_core.clocks import MissionTime, PhysicsTime, ReplayMapping


def test_pet_seek_changes_replay_without_advancing_physics():
    physics = PhysicsTime(12)
    epoch = datetime(2024, 5, 20, 5, 0, tzinfo=timezone.utc)
    mapping = ReplayMapping(epoch, MissionTime(100), rate=2)
    assert mapping.historical_utc(MissionTime(160)) == epoch + timedelta(seconds=120)
    assert mapping.historical_utc(MissionTime(40)) == epoch - timedelta(seconds=120)
    assert physics.seconds == 12


def test_replay_normalizes_timezone_to_utc():
    istanbul = timezone(timedelta(hours=3))
    epoch = datetime(2024, 5, 20, 8, 0, tzinfo=istanbul)
    result = ReplayMapping(epoch, MissionTime(0)).historical_utc(MissionTime(0))
    assert result == datetime(2024, 5, 20, 5, 0, tzinfo=timezone.utc)
    assert result.tzinfo is timezone.utc


@pytest.mark.parametrize("wrong", [PhysicsTime(5), 5.0, None])
def test_replay_rejects_physics_or_untyped_times(wrong):
    mapping = ReplayMapping(datetime.now(timezone.utc), MissionTime(0))
    with pytest.raises(TypeError):
        mapping.historical_utc(wrong)
    with pytest.raises(TypeError):
        ReplayMapping(datetime.now(timezone.utc), wrong)


@pytest.mark.parametrize("clock", [MissionTime, PhysicsTime])
@pytest.mark.parametrize("value", [-1, math.nan, math.inf, -math.inf])
def test_elapsed_time_must_be_finite_nonnegative(clock, value):
    with pytest.raises(ValueError):
        clock(value)


@pytest.mark.parametrize("rate", [0, -1, math.inf, math.nan])
def test_replay_rate_is_explicit_positive_finite(rate):
    with pytest.raises(ValueError):
        ReplayMapping(datetime.now(timezone.utc), MissionTime(0), rate)


def test_naive_historical_epoch_is_rejected():
    with pytest.raises(ValueError):
        ReplayMapping(datetime(2024, 5, 20), MissionTime(0))


@pytest.mark.parametrize(("seconds", "rate"), [(1e308, 1), (1e308, 10), (1e12, 1)])
def test_replay_rejects_unrepresentable_utc(seconds, rate):
    mapping = ReplayMapping(datetime(2024, 5, 20, tzinfo=timezone.utc), MissionTime(0), rate)
    with pytest.raises(ValueError, match="representable UTC"):
        mapping.historical_utc(MissionTime(seconds))
