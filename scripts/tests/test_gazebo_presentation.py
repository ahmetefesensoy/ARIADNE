"""Model identity, height/orientation and stamps must survive display routing."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('presentation', Path(__file__).parents[1] / 'gazebo_presentation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_body_identity_not_array_order_and_full_pose_stamp_preserved():
    value = {'header': {'stamp': {'sec': 123, 'nsec': 456}}, 'pose': [
        {'name': 'wheel_fl_link'}, {'name': 'rover_1', 'position': {'x': 145., 'y': -319., 'z': -3597.4},
        'orientation': {'x': .1, 'y': .2, 'z': .3, 'w': (.86)**.5}}]}
    sec, nano, xyz, quat = module.body_record(value)
    assert (sec, nano) == (123, 456)
    assert xyz == [145., -319., -3597.4]
    assert quat[:3] == [.1, .2, .3]
    assert value['pose'][1]['position']['z'] == -3597.4
    value['pose'].append(value['pose'][1])
    with pytest.raises(ValueError):
        module.body_record(value)


def test_invalid_physical_pose_is_rejected():
    for value in ({'pose': []}, {'pose': [{'name': 'rover_1', 'position': {'z': float('nan')}}]},
                  {'pose': [{'name': 'rover_1', 'orientation': {'w': 2.}}]}):
        with pytest.raises(ValueError):
            module.body_record(value)
