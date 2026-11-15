import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('tablet_stream',Path(__file__).parents[1]/'rviz_tablet_stream.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_stale_physics_or_odometry_never_live():
    assert m.source_fresh(10,9.5,9.5,True)
    assert not m.source_fresh(10,7,9.5,True)
    assert not m.source_fresh(10,9.5,7,True)
    assert not m.source_fresh(10,9.5,9.5,False)
    assert not m.source_fresh(10,11,9.5,True)
