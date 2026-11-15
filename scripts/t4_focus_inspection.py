"""Restore the existing technical inspection camera; do not edit/save assets.

Run with UnrealEditor's -ExecCmds="py <this file>". Unlit is an editor diagnostic
view mode, not a material or lighting design and not final visual acceptance.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import unreal

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
camera = next(actor for actor in actors.get_all_level_actors()
              if actor.get_actor_label() == 'T4_InspectionCamera')
actors.clear_actor_selection_set()
# Python's reflected Rotator constructor order differs from C++ positional
# expectations. Keywords avoid the fixture's pitch/yaw swap (straight down).
editor.set_level_viewport_camera_info(camera.get_actor_location(),
    unreal.Rotator(pitch=-30.0, yaw=-90.0, roll=0.0))
world = editor.get_editor_world()
unreal.SystemLibrary.execute_console_command(world, 'viewmode unlit')
location, rotation = editor.get_level_viewport_camera_info()
report = {'observed_at_utc': datetime.now(timezone.utc).isoformat(),
          'scope': 'existing technical camera, editor view only; no assets saved',
          'camera': camera.get_actor_label(),
          'viewport_location_cm': [location.x, location.y, location.z],
          'viewport_rotation_deg': [rotation.pitch, rotation.yaw, rotation.roll],
          'requested_view_mode': 'unlit', 'final_visual_acceptance': False}
report_path = Path(__file__).resolve().parents[1] / 'test-results/t4-inspection-camera.json'
report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
unreal.log('REDLINE inspection camera restored: ' + str(report_path))
