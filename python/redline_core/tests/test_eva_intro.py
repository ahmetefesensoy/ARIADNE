import math
import pytest
from redline_core.eva_intro import IntroLocations, advance_intro

POINTS = IntroLocations((0, 0), (16, 0))


def test_orientation_keeps_one_order_and_returns_home():
    phase = 0
    for position, expected in [((0, 0), 2), ((16, 0), 3), ((16, 0), 4), ((0, 0), 6)]:
        phase, event = advance_intro(phase, position, .1, POINTS)
        assert phase == expected and event
    with pytest.raises(ValueError): advance_intro(phase, (0, 0), .1, POINTS)


@pytest.mark.parametrize("age,position", [(2.01, (0, 0)), (-1, (0, 0)), (math.nan, (0, 0)),
                                         (.1, None), (.1, (math.nan, 0)), (.1, (0, math.inf))])
def test_unknown_or_stale_position_cannot_advance(age, position):
    with pytest.raises(ValueError): advance_intro(0, position, age, POINTS)


@pytest.mark.parametrize("phase,position", [(0, (16, 0)), (2, (0, 0)), (3, (0, 0)), (4, (16, 0)),
                                          (5, (0, 0)), (1, (0, 0)), (6, (0, 0))])
def test_remote_or_incompatible_phase_is_rejected(phase, position):
    with pytest.raises(ValueError): advance_intro(phase, position, .1, POINTS)
