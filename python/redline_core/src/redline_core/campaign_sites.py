"""SCENARIO chapter placement constrained by the real return field and fine tiles.

Names ridge/hollow are narrative classes here, not inferred mineralogy or a
claimed NASA sample location. The selection policy is authored and recorded.
"""
import math
import numpy as np


def select_field_points(grid, time_eps_s, habitat_xy, fine_bounds):
    time_eps_s=np.asarray(time_eps_s,dtype=float)
    if time_eps_s.shape!=(grid.height,grid.width) or len(habitat_xy)!=2 or not all(math.isfinite(v) for v in habitat_xy):
        raise ValueError("aligned return time and finite habitat required")
    y,x=np.mgrid[:grid.height,:grid.width]
    xx=grid.origin_xy[0]+(x+.5)*grid.resolution_m
    yy=grid.origin_xy[1]+(y+.5)*grid.resolution_m
    distance=np.hypot(xx-habitat_xy[0],yy-habitat_xy[1])
    supported=np.zeros(time_eps_s.shape,dtype=bool)
    for lo_x,lo_y,hi_x,hi_y in fine_bounds:
        supported|=(xx>=lo_x+15)&(xx<=hi_x-15)&(yy>=lo_y+15)&(yy<=hi_y-15)
    eligible=(supported & np.isfinite(time_eps_s) & (time_eps_s>=720)&(time_eps_s<=1080)
              & (distance>=280)&(distance<=430)&np.isfinite(grid.layer("slope_deg"))&(grid.layer("slope_deg")<10))
    chosen={}
    for target,offset in (("BXW_RIDGE_A",(-320,70)),("BXW_HOLLOW_B",(-260,150))):
        mask=eligible.copy()
        for point in chosen.values():mask&=np.hypot(xx-point[0],yy-point[1])>=40
        score=(xx-habitat_xy[0]-offset[0])**2+(yy-habitat_xy[1]-offset[1])**2
        if not mask.any():raise ValueError("no supported field target in the 12–18 min return band")
        cell=np.unravel_index(np.argmin(np.where(mask,score,np.inf)),score.shape)
        chosen[target]=tuple(float(v) for v in grid.cell_center(*cell))
    return chosen
