import importlib.util
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('surface',Path(__file__).parents[1]/'package_t3_surface.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_asymmetric_uvs_keep_north_up_and_geometry_unchanged(tmp_path):
    src=tmp_path/'source.obj';dst=tmp_path/'visual.obj'
    src.write_text('v 0 0 0\nv 10 0 1\nv 0 10 2\nvn 0 0 1\nf 1//1 2//1 3//1\n')
    tile={'pose_map_m':[100,200,-3000,0,0,0]}
    result=m.add_uv(src,dst,tile,[100,200,110,210],'terrain_ops')
    assert result['uvs']==3
    assert m.geometry_signature(src)==m.geometry_signature(dst)
    text=dst.read_text()
    assert 'vt 0.000000000000 0.000000000000' in text
    assert 'vt 1.000000000000 0.000000000000' in text
    assert 'vt 0.000000000000 1.000000000000' in text
    assert 'f 1/1/1 2/2/1 3/3/1' in text
    changed=tmp_path/'changed.obj';changed.write_text(src.read_text().replace('v 0 0 0','v 0 0 1'))
    assert m.geometry_signature(src)!=m.geometry_signature(changed)


def test_uv_export_rejects_outside_atlas(tmp_path):
    src=tmp_path/'source.obj';src.write_text('v 100 0 0\nvn 0 0 1\nf 1//1 1//1 1//1\n')
    with pytest.raises(ValueError,match='outside'):
        m.add_uv(src,tmp_path/'bad.obj',{'pose_map_m':[0,0,0,0,0,0]},[0,0,1,1],'m')
