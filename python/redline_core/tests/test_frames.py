"""Independent basis/rotation checks for the ROS↔UE coordinate contract."""
import itertools
import math

import pytest

from redline_core.frames import (
    ros_to_unreal_position, unreal_to_ros_position,
    ros_to_unreal_quaternion, unreal_to_ros_quaternion,
)


@pytest.mark.parametrize(("point", "expected"), [
    ((1, 0, 0), (100, 0, 0)), ((0, 1, 0), (0, -100, 0)),
    ((-1, 0, 0), (-100, 0, 0)), ((0, -1, 0), (0, 100, 0)),
    ((0, 0, 1), (0, 0, 100)), ((0, 0, -1), (0, 0, -100)),
])
def test_cardinal_axes_metres_to_centimetres(point, expected):
    assert ros_to_unreal_position(point) == pytest.approx(expected)
    assert unreal_to_ros_position(expected) == pytest.approx(point)


def test_one_metre_cube_edges_remain_one_hundred_centimetres():
    points = list(itertools.product((0, 1), repeat=3))
    for a, b in itertools.combinations(points, 2):
        if math.dist(a, b) == 1:
            assert math.dist(ros_to_unreal_position(a), ros_to_unreal_position(b)) == 100


def _rotate(q, v):
    # Quaternion rotation evaluated independently, v + 2w(q×v) + 2q×(q×v).
    x, y, z, w = q
    cross = (y*v[2]-z*v[1], z*v[0]-x*v[2], x*v[1]-y*v[0])
    second = (y*cross[2]-z*cross[1], z*cross[0]-x*cross[2], x*cross[1]-y*cross[0])
    return tuple(v[i] + 2*w*cross[i] + 2*second[i] for i in range(3))


@pytest.mark.parametrize("angle", [math.pi/2, -math.pi/2])
def test_yaw_sign_reverses(angle):
    q = (0, 0, math.sin(angle/2), math.cos(angle/2))
    ue = ros_to_unreal_quaternion(q)
    assert _rotate(ue, (1, 0, 0)) == pytest.approx((0, -math.sin(angle), 0), abs=1e-12)
    assert unreal_to_ros_quaternion(ue) == pytest.approx(q)


@pytest.mark.parametrize("axis", [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 2, 3)])
def test_rotation_and_position_conversion_commute(axis):
    n = math.hypot(*axis)
    q = tuple(math.sin(.7)*x/n for x in axis) + (math.cos(.7),)
    v = (2.4, -3.1, 5.7)
    expected = ros_to_unreal_position(_rotate(q, v))
    actual = _rotate(ros_to_unreal_quaternion(q), ros_to_unreal_position(v))
    assert actual == pytest.approx(expected)


@pytest.mark.parametrize("bad", [(1, 2), (1, 2, 3, 4), (math.nan, 0, 0), (math.inf, 0, 0)])
@pytest.mark.parametrize("convert", [ros_to_unreal_position, unreal_to_ros_position])
def test_rejects_malformed_positions(convert, bad):
    with pytest.raises(ValueError):
        convert(bad)


@pytest.mark.parametrize("bad", [(0, 0, 0, 0), (1, 1, 0, 0), (0, 0, math.nan, 1), (0, 0, 1)])
@pytest.mark.parametrize("convert", [ros_to_unreal_quaternion, unreal_to_ros_quaternion])
def test_rejects_nonunit_or_malformed_quaternions(convert, bad):
    with pytest.raises(ValueError):
        convert(bad)


def test_rejects_position_scale_overflow():
    with pytest.raises(ValueError):
        ros_to_unreal_position((1e308, 0, 0))
