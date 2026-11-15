"""Stage a passive campaign RViz view from the actual per-run rover spawn.

Only diagnostic display topics use the raised map plane. Original Nav2 maps,
paths, odometry, transforms and command topics remain unchanged. This helper
does not create a ROS node or publish a command.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import yaml


VIEW_FRAME = "redline/navigation_view"
DRAWING_TOPICS = {
    "/rover_1/map": "/redline/view/map",
    "/rover_1/global_costmap/costmap": "/redline/view/global_costmap/costmap",
    "/rover_1/plan": "/redline/view/plan",
}
PASSIVE_DISPLAYS = {
    "rviz_default_plugins/Map", "rviz_default_plugins/RobotModel",
    "rviz_default_plugins/LaserScan", "rviz_default_plugins/PointCloud2",
    "rviz_default_plugins/Path", "rviz_default_plugins/Polygon",
    "rviz_default_plugins/TF",
}


def campaign_configuration(template, terrain):
    """Return a separate view; reject unsupported spawn or display contracts."""
    spawn = terrain["spawn"]
    focus = []
    for key in ("map_x_m", "map_y_m", "ground_z_m"):
        value = spawn[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Campaign RViz requires finite numeric spawn " + key)
        focus.append(float(value))
    result = deepcopy(template)
    manager = result["Visualization Manager"]
    manager["Global Options"]["Fixed Frame"] = VIEW_FRAME
    manager["Global Options"]["Frame Rate"] = 15
    # No SetGoal, InitialPose, PublishPoint or interactive command tool. Mission
    # actions remain the only campaign owner of Nav2 goals.
    manager["Tools"] = [
        {"Class": "rviz_default_plugins/MoveCamera"},
        {"Class": "rviz_default_plugins/Select"},
    ]
    for display in manager["Displays"]:
        kind = display.get("Class")
        if kind not in PASSIVE_DISPLAYS:
            raise ValueError("Unsupported display in passive campaign view: " + str(kind))
        topic = display.get("Topic")
        if isinstance(topic, dict) and topic.get("Value") in DRAWING_TOPICS:
            topic["Value"] = DRAWING_TOPICS[topic["Value"]]
        # The default campaign has a measured 2D scan. Do not imply that the
        # optional 3D segmentation stream is running merely by showing a box.
        if kind == "rviz_default_plugins/PointCloud2":
            display["Enabled"] = False
        if kind == "rviz_default_plugins/TF":
            display["Enabled"] = False
    view = manager["Views"]["Current"]
    view.update({"Target Frame": VIEW_FRAME, "X": focus[0], "Y": focus[1],
                 "Scale": 45, "Angle": 0})
    result["Window Geometry"].update({"Width": 1000, "Height": 760})
    return result, focus


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terrain", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--template", type=Path,
                        default=root/"ros_ws/src/redline_navigation/rviz/navigation.rviz")
    args = parser.parse_args()
    terrain = json.loads(args.terrain.read_text())
    configuration, focus = campaign_configuration(yaml.safe_load(args.template.read_text()), terrain)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(yaml.safe_dump(configuration, sort_keys=False, allow_unicode=True))
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_terrain": str(args.terrain.resolve()),
        "source_terrain_sha256": hashlib.sha256(args.terrain.read_bytes()).hexdigest(),
        "source_template_sha256": hashlib.sha256(args.template.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
        "focus_map_xyz_m": focus, "fixed_frame": VIEW_FRAME,
        "passive": True, "command_tools": [],
        "note": "Spawn comes from the staged SCENARIO manifest. Raised drawings are presentation copies; Nav2 input frames/topics are untouched.",
    }
    args.out.with_suffix(".json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
