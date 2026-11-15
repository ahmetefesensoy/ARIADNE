import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

spec=importlib.util.spec_from_file_location('prepare_world',Path(__file__).parents[1]/'scripts/prepare_world.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_mars_world_requires_same_visual_collision_and_no_implicit_fuel(tmp_path):
    rover=tmp_path/'rover.sdf';rover.write_text('<sdf><model name="rover_1"><link name="base_link"/></model></sdf>')
    tree=m.assemble(rover,smoke=True);world=tree.find('world')
    assert world.findtext('gravity')=='0 0 -3.721'
    assert float(world.findtext('physics/real_time_factor'))==1
    assert float(world.findtext('physics/max_step_size'))==.001
    assert not tree.findall('.//include')
    assert world.find("model[@name='rover_1']/pose").text=='0 0 0.6 0 0 0'
    camera=world.find("gui/plugin[@filename='MinimalScene']/camera_pose").text
    assert camera=='-65 -65 80 0 0.715 0.785398'


def test_geometry_signature_checks_positions_but_ignores_visual_uv(tmp_path):
    collision=tmp_path/'collision.obj';visual=tmp_path/'visual.obj'
    collision.write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1//1 2//1 3//1\n')
    visual.write_text('v 0 0 0\nvt 0 0\nv 1 0 0\nvt 1 0\nv 0 1 0\nvt 0 1\nf 1/1/1 2/2/1 3/3/1\n')
    assert m.geometry_signature(collision)==m.geometry_signature(visual)
    visual.write_text(visual.read_text().replace('v 1 0 0','v 2 0 0'))
    assert m.geometry_signature(collision)!=m.geometry_signature(visual)


def test_obstacle_fixture_is_explicit_and_has_real_collision(tmp_path):
    rover=tmp_path/'rover.sdf';rover.write_text('<sdf><model name="rover_1"><link name="base_link"/></model></sdf>')
    assert m.assemble(rover,smoke=True).find(".//model[@name='SCENARIO_lidar_acceptance_obstacle']") is None
    tree=m.assemble(rover,smoke=True,root_clearance=.9,obstacle_fixture=True)
    obstacle=tree.find(".//model[@name='SCENARIO_lidar_acceptance_obstacle']")
    assert obstacle.findtext('pose')=='5.0 0.0 1.5 0 0 0'
    assert obstacle.findtext('link/collision/geometry/box/size')==obstacle.findtext('link/visual/geometry/box/size')=='1 1 3.5'
    assert tree.find(".//model[@name='rover_1']/pose").text=='0 0 1.0 0 0 0'
    low=m.assemble(rover,smoke=True,obstacle_fixture=True,obstacle_height=.4)
    obstacle=low.find(".//model[@name='SCENARIO_lidar_acceptance_obstacle']")
    assert obstacle.findtext('link/collision/geometry/box/size')=='1 1 0.4'
    assert abs(float(obstacle.findtext('pose').split()[2])-.15)<1e-12


def test_fixture_uses_actual_collision_triangle_height_not_spawn_height(tmp_path):
    import pytest
    path=tmp_path/'mesh.obj'
    path.write_text('v 0 0 0\nv 2 0 2\nv 0 2 4\nf 1 2 3\n')
    manifest={'meshes':[{'role':'ops_1m','bounds_map_m':[10,20,12,22],
                         'pose_map_m':[10,20,-3500,0,0,0],'collision_uri':str(path)}]}
    assert m.terrain_height(manifest,10.5,20.5)==pytest.approx(-3498.5)
    with pytest.raises(ValueError,match='support'):m.terrain_height(manifest,13,20)
