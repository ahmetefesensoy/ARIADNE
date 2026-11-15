"""Display the exact SCENARIO Gazebo test boxes in a separate derived map.

No physics, collision or hidden obstacle map is sent to robot planning.
Existing cube geometry is a diagnostic fixture, not generated Martian art.
"""
import json
import os
from pathlib import Path
import unreal

repo = Path(os.environ['REDLINE_REPO'])
record = json.loads((repo/'test-results/autonomy-showcase-obstacles.json').read_text())
world = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world.load_level('/Game/DerivedPreview/BXW_LivePreview')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cube = unreal.load_asset('/Engine/BasicShapes/Cube.Cube')
fixtures = list(record['fixtures'])
# This original acceptance box already exists in Gazebo before extra insertion.
import xml.etree.ElementTree as ET
runtime = max((repo/'test-results').glob('t3-runtime-*/bxw.sdf'), key=lambda p:p.stat().st_mtime)
model = ET.parse(runtime).find(".//model[@name='SCENARIO_lidar_acceptance_obstacle']")
pose = list(map(float, model.findtext('pose').split()))
fixtures.append({'name': 'SCENARIO_lidar_acceptance_obstacle', 'map_xy_m': pose[:2],
                 'center_z_m': pose[2], 'size_m': [1., 1., 3.5]})
for item in fixtures:
    x,y = item['map_xy_m']
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,
        unreal.Vector(x*100,-y*100,item['center_z_m']*100))
    actor.set_actor_label(item['name'])
    actor.static_mesh_component.set_static_mesh(cube)
    actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    actor.static_mesh_component.set_simulate_physics(False)
    actor.set_actor_scale3d(unreal.Vector(*item['size_m']))
target = '/Game/DerivedPreview/BXW_Autonomy_Showcase'
if not unreal.EditorLoadingAndSavingUtils.save_map(
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(), target):
    raise RuntimeError('Showcase map save failed')
(repo/'test-results/t4-obstacle-showcase.json').write_text(json.dumps({
    'map': target, 'status': 'SCENARIO', 'visible_fixtures': len(fixtures),
    'physics': False, 'planner_input': False}, indent=2)+'\n')
