"""Diagnostic elevation must never alter the original navigation messages."""
import importlib.util
from pathlib import Path as FilePath
import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path, OccupancyGrid

spec = importlib.util.spec_from_file_location('view', FilePath(__file__).parents[1] / 'rviz_navigation_view.py')
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)


def test_map_and_path_copy_preserve_navigation_xy_and_stamp():
    message = Path()
    message.header.frame_id = 'map'
    message.header.stamp.sec = 123
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.pose.position.x = 145.0
    pose.pose.position.y = -299.0
    pose.pose.orientation.w = 1.0
    message.poses = [pose]
    result = view.at_inspection_height(message, -3598.0)
    assert message.poses[0].pose.position.z == 0.0
    assert result.poses[0].pose.position.z == pytest.approx(-3597.85)
    assert result.poses[0].pose.position.x == 145.0
    assert result.poses[0].pose.position.y == -299.0
    assert result.header == message.header
    assert result.poses[0].pose.orientation == pose.pose.orientation
    grid = OccupancyGrid()
    grid.header.frame_id = 'map'
    grid.info.origin.position.x = -500.0
    grid.data = [0, 100, -1]
    copy = view.at_inspection_height(grid, -3598.0)
    assert copy.info.origin.position.z == -3598.0
    assert grid.info.origin.position.z == 0.0
    assert copy.data == grid.data
    assert copy.info.origin.position.x == -500.0


def test_invalid_frame_and_nonfinite_elevation_are_rejected():
    path = Path()
    path.header.frame_id = 'odom'
    with pytest.raises(ValueError):
        view.at_inspection_height(path, -3598.0)
    path.header.frame_id = 'map'
    with pytest.raises(ValueError):
        view.at_inspection_height(path, float('nan'))
    pose = PoseStamped()
    pose.header.frame_id = 'odom'
    path.poses = [pose]
    with pytest.raises(ValueError):
        view.at_inspection_height(path, -3598.0)
