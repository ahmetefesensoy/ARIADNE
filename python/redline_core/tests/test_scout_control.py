import math
import pytest
from redline_core.scout_control import world_to_body_velocity,flight_velocity_setpoint


def test_full_body_inverse_removes_tilted_climb_coupling():
    # A 45-degree pitch must put a world-vertical command into both body X/Z.
    q=(0,math.sin(math.pi/8),0,math.cos(math.pi/8))
    actual=world_to_body_velocity((0,0,1.5),q)
    assert actual==pytest.approx((-1.5/math.sqrt(2),0,1.5/math.sqrt(2)))
    # Rotate the result back: plugin world velocity must remain purely vertical.
    world=world_to_body_velocity(actual,(0,-q[1],0,q[3]))
    assert world==pytest.approx((0,0,1.5))


@pytest.mark.parametrize('q',[(0,0,0,1),(0,0,math.sin(.6),math.cos(.6)),(.5,.5,.5,.5)])
def test_world_body_round_trip_and_norm(q):
    velocity=(2,-1,.8);body=world_to_body_velocity(velocity,q)
    assert sum(v*v for v in body)==pytest.approx(sum(v*v for v in velocity))
    assert world_to_body_velocity(body,(-q[0],-q[1],-q[2],q[3]))==pytest.approx(velocity)


def test_no_command_jump_on_waypoint_turn_and_diagonal_acceleration_bounded():
    previous=(2.,0.,.5);dt=.02
    current=flight_velocity_setpoint((-10,10,-3),previous,dt)
    assert math.hypot(current[0]-previous[0],current[1]-previous[1])<=.45*dt+1e-12
    assert abs(current[2]-previous[2])<=.65*dt+1e-12
    assert flight_velocity_setpoint((10,0,0),current,0)==current


def test_approach_slows_and_setpoint_stays_bounded():
    velocity=(0,0,0)
    for _ in range(500):velocity=flight_velocity_setpoint((100,100,100),velocity,.02)
    assert math.hypot(*velocity[:2])<=3.+1e-12 and abs(velocity[2])<=1.5
    for _ in range(500):velocity=flight_velocity_setpoint((.1,0,0),velocity,.02)
    assert velocity==pytest.approx((.065,0,0))


@pytest.mark.parametrize('dt',[float('nan'),-1,.3])
def test_invalid_or_stale_physics_delta_rejected(dt):
    with pytest.raises(ValueError):flight_velocity_setpoint((1,0,0),(0,0,0),dt)


def test_invalid_attitude_rejected():
    with pytest.raises(ValueError):world_to_body_velocity((1,0,0),(0,0,0,0))
    with pytest.raises(ValueError):world_to_body_velocity((float('nan'),0,0),(0,0,0,1))
