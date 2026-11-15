import numpy as np
import pytest
from redline_core.ground import GroundConfig,segment_ground


def scene(slope=(.05,-.03),height=.3):
    x,y=np.meshgrid(np.linspace(-6,6,35),np.linspace(-6,6,35))
    z=slope[0]*x+slope[1]*y-2.35
    floor=np.column_stack((x.ravel(),y.ravel(),z.ravel()))
    rng=np.random.default_rng(39);floor[:,2]+=rng.normal(0,.005,len(floor))
    bx,by=np.meshgrid(np.linspace(3,3.6,8),np.linspace(-.3,.3,8))
    rock=np.column_stack((bx.ravel(),by.ravel(),(slope[0]*bx+slope[1]*by-2.35+height).ravel()))
    return floor,rock


def test_sloped_floor_and_low_rock_are_separated_without_truth_input():
    floor,rock=scene();points=np.vstack((floor,rock,[[np.nan,0,0],[np.inf,0,0]]))
    result=segment_ground(points)
    assert result.valid,result.reason
    assert result.ground[:len(floor)].sum()>1000
    assert result.obstacles[len(floor):-2].all()
    assert not result.obstacles[:len(floor)].any()
    assert not result.obstacles[-2:].any()
    assert result.plane_z_abc==pytest.approx((.05,-.03,-2.35),abs=.003)
    assert np.array_equal(result.obstacles,segment_ground(points).obstacles)


def test_self_envelope_invalid_and_unobserved_data_do_not_become_clear_space():
    floor,rock=scene();points=np.vstack((floor,rock))
    result=segment_ground(points,self_bounds=[[2.8,-.5,-3],[3.8,.5,-1.8]])
    assert result.valid and not result.obstacles[len(floor):].any()
    for points in (np.empty((0,3)),np.full((100,3),np.nan),np.array([[i,0,-2.35] for i in np.linspace(1,5,100)])):
        failed=segment_ground(points)
        assert not failed.valid and not failed.ground.any() and not failed.obstacles.any()
    with pytest.raises(ValueError):segment_ground(floor,self_bounds=[[1,1,1],[0,0,0]])


def test_walls_steep_or_wrong_height_plane_fail_closed():
    floor,_=scene(slope=(.6,0))
    assert not segment_ground(floor).valid
    floor,_=scene();floor[:,2]+=1
    assert not segment_ground(floor).valid
    wall=np.column_stack((np.full(400,3.),np.tile(np.linspace(-3,3,20),20),np.repeat(np.linspace(-2.4,1,20),20)))
    assert not segment_ground(wall).valid


def test_borderline_height_and_outside_support_remain_unknown():
    floor,_=scene(slope=(0,0));extra=np.array([[4,0,-2.25],[12,0,-2.35],[5,0,-2.6]])
    result=segment_ground(np.vstack((floor,extra)))
    assert result.valid and not result.ground[-3:].any() and not result.obstacles[-3:].any()
    assert result.unknown[-3] and result.unknown[-1]
    assert not result.unknown[-2]  # beyond the declared local inference domain


def test_smooth_rise_is_ground_but_a_low_discrete_object_remains_an_obstacle():
    x,y=np.meshgrid(np.linspace(-6,6,55),np.linspace(-6,6,55))
    z=-2.35+.006*x*x+.003*y*y
    floor=np.column_stack((x.ravel(),y.ravel(),z.ravel()))
    bx,by=np.meshgrid(np.linspace(3,4,8),np.linspace(-.5,.5,8))
    rock=np.column_stack((bx.ravel(),by.ravel(),(-2.35+.006*bx*bx+.003*by*by+.35).ravel()))
    result=segment_ground(np.vstack((floor,rock)))
    assert result.valid,result.reason
    assert result.obstacles[:len(floor)].sum()==0
    assert result.ground[:len(floor)].mean()>.95
    assert result.obstacles[len(floor):].all()


@pytest.mark.parametrize('kwargs',[{'ground_tolerance_m':-.1},{'max_slope_deg':90},{'trials':0},
                                   {'minimum_support_fraction':0},{'expected_ground_z_m':float('nan')}])
def test_invalid_thresholds_rejected(kwargs):
    with pytest.raises(ValueError):GroundConfig(**kwargs)
