import numpy as np
import pytest
from redline_core.grid import Grid
from redline_core.campaign_sites import select_field_points


def test_field_points_require_support_return_band_walkability_and_separation():
    grid=Grid((-500.,-500.),4.,250,250,{"slope_deg":np.zeros((250,250))})
    times=np.full((250,250),900.)
    bounds=[(-500.,-500.,500.,500.)]
    points=select_field_points(grid,times,(290.,-454.),bounds)
    a,b=points.values()
    assert np.linalg.norm(np.array(a)-b)>=40
    for point in points.values():
        assert 280<=np.linalg.norm(np.array(point)-[290,-454])<=430
        assert -485<=point[0]<=485 and -485<=point[1]<=485
    times[:]=np.inf
    with pytest.raises(ValueError):select_field_points(grid,times,(290.,-454.),bounds)


def test_no_target_is_selected_without_matching_grid_or_walkable_fine_support():
    grid=Grid((0.,0.),4.,10,10,{"slope_deg":np.full((10,10),30.)})
    with pytest.raises(ValueError):select_field_points(grid,np.ones((2,2)),(0,0),[])
    with pytest.raises(ValueError):select_field_points(grid,np.full((10,10),900.),(0,0),[(0,0,40,40)])
