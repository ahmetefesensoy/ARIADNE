"""Local ENU metres ↔ Unreal centimetres, per proje.md §4.2.

These conversions do not project latitude/longitude or choose a Mars datum.
Quaternion ordering is always (x, y, z, w), including Unreal FQuat.
"""
from __future__ import annotations

import math
from collections.abc import Iterable

Vector3 = tuple[float, float, float]
Quaternion = tuple[float, float, float, float]


def _finite(values: Iterable[float], length: int) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if len(result) != length or not all(math.isfinite(v) for v in result):
        raise ValueError(f"Expected {length} finite coordinates")
    return result


def ros_to_unreal_position(position_m: Iterable[float]) -> Vector3:
    """Map ROS ENU metres to Unreal centimetres, reflecting the Y axis."""
    x, y, z = _finite(position_m, 3)
    result = (100.0 * x, -100.0 * y, 100.0 * z)
    return _finite(result, 3)


def unreal_to_ros_position(position_cm: Iterable[float]) -> Vector3:
    """Inverse position conversion; input must use the same local origin."""
    x, y, z = _finite(position_cm, 3)
    return (x / 100.0, -y / 100.0, z / 100.0)


def _unit_quaternion(values: Iterable[float]) -> Quaternion:
    result = _finite(values, 4)
    if not math.isclose(math.hypot(*result), 1.0, abs_tol=1e-6, rel_tol=0):
        raise ValueError("Expected a unit quaternion in (x, y, z, w) order")
    return result


def ros_to_unreal_quaternion(quaternion_xyzw: Iterable[float]) -> Quaternion:
    """Change handedness by conjugating the rotation with diag(1,-1,1)."""
    x, y, z, w = _unit_quaternion(quaternion_xyzw)
    return (-x, y, -z, w)


def unreal_to_ros_quaternion(quaternion_xyzw: Iterable[float]) -> Quaternion:
    """Inverse handedness conversion, in (x, y, z, w) order."""
    x, y, z, w = _unit_quaternion(quaternion_xyzw)
    return (-x, y, -z, w)
