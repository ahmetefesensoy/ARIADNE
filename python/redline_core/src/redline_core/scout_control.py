"""Bounded SCENARIO scout setpoints, independent of ROS and presentation.

The Gazebo Lee controller consumes full body-frame linear velocity, including
roll and pitch. These helpers do not estimate flight state or set physical poses.
"""
from __future__ import annotations

import math


def world_to_body_velocity(velocity, quaternion_xyzw):
    """Apply R(q).transpose to a world velocity, with finite/unit guards."""
    if len(velocity)!=3 or len(quaternion_xyzw)!=4:
        raise ValueError("3-vector velocity and unit XYZW quaternion required")
    if not all(math.isfinite(v) for v in (*velocity,*quaternion_xyzw)):
        raise ValueError("Finite flight state required")
    x,y,z,w=quaternion_xyzw
    if abs(sum(v*v for v in quaternion_xyzw)-1)>.001:
        raise ValueError("Unit attitude quaternion required")
    # Conjugate rotation through two cross products. This handles arbitrarily
    # tilted aircraft; a yaw-only transform couples climb speed into XY motion.
    x,y,z=-x,-y,-z
    vx,vy,vz=velocity
    tx,ty,tz=2*(y*vz-z*vy),2*(z*vx-x*vz),2*(x*vy-y*vx)
    return (vx+w*tx+y*tz-z*ty,vy+w*ty+z*tx-x*tz,vz+w*tz+x*ty-y*tx)


def flight_velocity_setpoint(delta, previous, dt, *, speed=3., horizontal_accel=.45,
                             vertical_accel=.65, position_gain=.65):
    """Brake toward a waypoint and slew velocity by actual physics delta time.

    Horizontal acceleration is norm-bounded; diagonal requests do not receive
    sqrt(2) extra acceleration. A zero dt holds the last command. Long gaps are
    rejected so wall time cannot advance a paused physics trajectory.
    """
    if len(delta)!=3 or len(previous)!=3 or not all(math.isfinite(v) for v in (*delta,*previous,dt,speed,horizontal_accel,vertical_accel,position_gain)):
        raise ValueError("Finite 3-vector state and control parameters required")
    if not 0<=dt<=.25 or not 0<speed<=5 or not 0<horizontal_accel<=1 or not 0<vertical_accel<=1.5 or not 0<position_gain<=2:
        raise ValueError("Bounded physics step, speed and acceleration required")
    horizontal=math.hypot(delta[0],delta[1])
    desired_speed=min(speed,position_gain*horizontal,math.sqrt(2*horizontal_accel*horizontal))
    if horizontal:
        desired_x,desired_y=delta[0]/horizontal*desired_speed,delta[1]/horizontal*desired_speed
    else:desired_x=desired_y=0.
    desired_z=math.copysign(min(1.5,position_gain*abs(delta[2]),math.sqrt(2*vertical_accel*abs(delta[2]))),delta[2])
    change_x,change_y=desired_x-previous[0],desired_y-previous[1]
    change_norm=math.hypot(change_x,change_y)
    scale=min(1.,horizontal_accel*dt/change_norm) if change_norm else 1.
    limit=vertical_accel*dt
    return (previous[0]+change_x*scale,previous[1]+change_y*scale,
            previous[2]+max(-limit,min(limit,desired_z-previous[2])))
