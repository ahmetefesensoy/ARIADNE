import importlib.util
import math
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('clearance',Path(__file__).parents[1]/'analyze_t3_clearance.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
SQUARE=[(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]


def test_touching_and_contained_envelopes_have_zero_clearance():
    assert m.polygon_distance(SQUARE,m.transform(SQUARE,1,0,0))==0
    assert m.polygon_distance(SQUARE,[(x/2,y/2) for x,y in SQUARE])==0


def test_separated_and_diagonal_clearances_are_geometric():
    assert m.polygon_distance(SQUARE,m.transform(SQUARE,2,0,0))==pytest.approx(1)
    assert m.polygon_distance(SQUARE,m.transform(SQUARE,2,2,0))==pytest.approx(math.sqrt(2))


def test_common_rotation_and_translation_preserve_distance():
    other=m.transform(SQUARE,2,0,0)
    assert m.polygon_distance(m.transform(SQUARE,145,-3598,.7),m.transform(other,145,-3598,.7))==pytest.approx(1)
