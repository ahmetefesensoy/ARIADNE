"""A campaign observer must focus the actual rover without acquiring command authority."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("campaign_rviz", ROOT/"scripts/prepare_campaign_rviz.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def template():
    return yaml.safe_load((ROOT/"ros_ws/src/redline_navigation/rviz/navigation.rviz").read_text())


def test_field_view_keeps_original_navigation_contract_and_has_no_command_tools():
    original = template()
    before = deepcopy(original)
    terrain = {"spawn": {"map_x_m": -40., "map_y_m": -382., "ground_z_m": -3596.434}}
    result, focus = helper.campaign_configuration(original, terrain)
    assert original == before
    assert focus == [-40., -382., -3596.434]
    manager = result["Visualization Manager"]
    assert manager["Global Options"]["Fixed Frame"] == helper.VIEW_FRAME
    assert manager["Views"]["Current"]["Target Frame"] == helper.VIEW_FRAME
    assert (manager["Views"]["Current"]["X"], manager["Views"]["Current"]["Y"]) == (-40., -382.)
    assert {tool["Class"] for tool in manager["Tools"]} == {
        "rviz_default_plugins/MoveCamera", "rviz_default_plugins/Select"}
    by_name = {display["Name"]: display for display in manager["Displays"]}
    assert by_name["Global plan"]["Topic"]["Value"] == "/redline/view/plan"
    assert by_name["DEM slope occupancy map"]["Topic"]["Value"] == "/redline/view/map"
    assert by_name["LiDAR"]["Topic"] == next(d["Topic"] for d in before["Visualization Manager"]["Displays"] if d["Name"] == "LiDAR")
    assert by_name["Local costmap - live LiDAR"]["Topic"]["Value"] == "/rover_1/local_costmap/costmap"
    assert by_name["Local footprint"]["Topic"]["Value"] == "/rover_1/local_costmap/published_footprint"
    assert by_name["Rover"]["Description Topic"]["Value"] == "/rover_1/robot_description"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "-3596.4"])
def test_invalid_spawn_cannot_make_a_misleading_view(value):
    terrain = {"spawn": {"map_x_m": -40., "map_y_m": -382., "ground_z_m": value}}
    with pytest.raises(ValueError, match="finite numeric spawn"):
        helper.campaign_configuration(template(), terrain)


def test_unreviewed_interactive_display_does_not_enter_a_passive_campaign():
    source = template()
    source["Visualization Manager"]["Displays"].append({
        "Class": "rviz_default_plugins/InteractiveMarkers", "Name": "Unreviewed control"})
    with pytest.raises(ValueError, match="Unsupported display"):
        helper.campaign_configuration(source, {"spawn": {"map_x_m": 0., "map_y_m": 0., "ground_z_m": 0.}})
