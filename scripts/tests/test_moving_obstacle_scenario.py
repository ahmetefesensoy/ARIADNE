"""Bounded SCENARIO crossing path and physics-time speed."""
import importlib.util
from pathlib import Path
import math

spec=importlib.util.spec_from_file_location('moving',Path(__file__).parents[1]/'moving_obstacle_scenario.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_continuous_bounded_crossing_speed():
    for phase in (0,1.7):
        for index in range(2000):
            t=index*.05
            assert abs(module.trajectory(t,phase))<=3
            speed=(module.trajectory(t+.001,phase)-module.trajectory(t,phase))/.001
            assert abs(speed)<=.25001
    assert abs(module.trajectory(24*math.pi))<1e-10
