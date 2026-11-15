"""Local plane segmentation from measured XYZ only; no DEM/world-object input.

SCENARIO thresholds define a commissioning sensor model, not validated Mars
terrain semantics. A single plane cannot resolve cliffs, holes, banks or dunes.
Failure returns no free-space evidence. All masks index the original input.
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy.spatial import cKDTree


@dataclass(frozen=True)
class GroundConfig:
    expected_ground_z_m: float = -2.35
    intercept_tolerance_m: float = .5
    fit_radius_m: float = 8.0
    ground_tolerance_m: float = .08
    obstacle_height_m: float = .14
    max_obstacle_height_m: float = 3.0
    max_slope_deg: float = 20.0
    minimum_support: int = 40
    minimum_support_fraction: float = .45
    trials: int = 64
    seed: int = 417
    local_surface_radius_m: float = 1.5

    def __post_init__(self):
        for key in ('expected_ground_z_m','intercept_tolerance_m','fit_radius_m','ground_tolerance_m',
                    'obstacle_height_m','max_obstacle_height_m','max_slope_deg','minimum_support_fraction','local_surface_radius_m'):
            if not math.isfinite(getattr(self,key)):raise ValueError('Non-finite ground configuration')
        if not (self.intercept_tolerance_m>0 and self.fit_radius_m>0 and
                0<self.ground_tolerance_m<self.obstacle_height_m<self.max_obstacle_height_m and
                0<self.max_slope_deg<45 and 0<self.minimum_support_fraction<=1 and
                self.minimum_support>=10 and 1<=self.trials<=256 and .8<=self.local_surface_radius_m<=2):
            raise ValueError('Invalid ground configuration')


@dataclass
class GroundResult:
    valid: bool
    reason: str
    ground: np.ndarray
    obstacles: np.ndarray
    unknown: np.ndarray
    plane_z_abc: tuple | None
    support_fraction: float
    fit_rms_m: float | None


def segment_ground(points, config=GroundConfig(), *, self_bounds=None):
    """Fit z=ax+by+c robustly in the sensor frame and classify local returns.

    self_bounds is the explicitly staged sensor-relative robot envelope. It is
    used only to reject self returns; external object locations are never input.
    Outputs beyond fit_radius are unknown, not extrapolated ground/free space.
    """
    p=np.asarray(points,dtype=np.float64)
    if p.ndim!=2 or p.shape[1]!=3:raise ValueError('Expected N x 3 XYZ points')
    n=len(p);eligible=np.isfinite(p).all(axis=1)
    eligible &= np.hypot(p[:,0],p[:,1])<=config.fit_radius_m
    eligible &= np.hypot(p[:,0],p[:,1])>=.3
    if self_bounds is not None:
        bounds=np.asarray(self_bounds,dtype=float)
        if bounds.shape!=(2,3) or not np.isfinite(bounds).all() or np.any(bounds[0]>=bounds[1]):
            raise ValueError('Invalid sensor-relative self envelope')
        eligible &= ~np.all((p>=bounds[0])&(p<=bounds[1]),axis=1)
    zero=np.zeros(n,dtype=bool)
    def failure(reason):return GroundResult(False,reason,zero.copy(),zero.copy(),eligible.copy(),None,0.,None)
    indices=np.flatnonzero(eligible);local=p[indices]
    if len(local)<config.minimum_support:return failure('insufficient_finite_local_returns')
    # Cell minima reduce dense wall/rock faces dominating random sampling.
    cells=np.floor(local[:,:2]/.4).astype(np.int64)
    order=np.lexsort((local[:,2],cells[:,1],cells[:,0]))
    sorted_cells=cells[order]
    first=np.r_[True,np.any(np.diff(sorted_cells,axis=0)!=0,axis=1)]
    seeds=local[order[first]]
    if len(seeds)<12:return failure('insufficient_spatial_support')
    rng=np.random.default_rng(config.seed);best=None;best_score=-1
    design=np.column_stack((local[:,:2],np.ones(len(local))))
    def plausible(plane):
        return (np.isfinite(plane).all() and math.hypot(*plane[:2])<=math.tan(math.radians(config.max_slope_deg))
                and abs(plane[2]-config.expected_ground_z_m)<=config.intercept_tolerance_m)
    for _ in range(config.trials):
        sample=seeds[rng.choice(len(seeds),3,replace=False)]
        matrix=np.column_stack((sample[:,:2],np.ones(3)))
        if abs(np.linalg.det(matrix))<.05:continue
        plane=np.linalg.solve(matrix,sample[:,2])
        if not plausible(plane):continue
        residual=local[:,2]-design@plane
        inlier=np.abs(residual)<=config.ground_tolerance_m
        score=int(inlier.sum())
        # Reject raised platforms as the ground if substantial evidence exists
        # below their proposed plane. No cloud-history or simulator oracle.
        if np.mean(residual<-.15)>.1:continue
        if score>best_score:best,best_score=(plane,inlier),score
    if best is None:return failure('no_plausible_ground_plane')
    plane,inlier=best
    if best_score<config.minimum_support or best_score/len(local)<config.minimum_support_fraction:
        return failure('insufficient_plane_consensus')
    plane=np.linalg.lstsq(design[inlier],local[inlier,2],rcond=None)[0]
    if not plausible(plane):return failure('refined_plane_outside_limits')
    residual=local[:,2]-design@plane;ground_local=np.abs(residual)<=config.ground_tolerance_m
    support=float(ground_local.mean())
    support_xy=local[ground_local,:2]
    if len(support_xy)<config.minimum_support or support<config.minimum_support_fraction:
        return failure('refined_plane_insufficient_consensus')
    # Demand 2D support, not a line of points on one laser ring or wall.
    if np.linalg.eigvalsh(np.cov(support_xy,rowvar=False)).min()<.25:
        return failure('ground_support_is_degenerate')
    # The global fit validates a nearby ground support; it must not turn a
    # smooth local rise into a vertical rock. Refine from spatial cell minima
    # around each observed cell, fitting the lower 60% after global detrending.
    # Every refinement requires 2D observed support, bounded slope and residual.
    # Broad raised platforms (> neighbourhood diameter) remain ambiguous.
    seed_design=np.column_stack((seeds[:,:2],np.ones(len(seeds))))
    seed_residual=seeds[:,2]-seed_design@plane
    tree=cKDTree(seeds[:,:2]);local_planes=np.repeat(plane[None,:],len(seeds),axis=0)
    for i,neighbours in enumerate(tree.query_ball_point(seeds[:,:2],config.local_surface_radius_m)):
        if len(neighbours)<12:continue
        neighbours=np.asarray(neighbours)
        candidates=neighbours[seed_residual[neighbours]<=np.quantile(seed_residual[neighbours],.6)]
        if len(candidates)<6:continue
        xy=seeds[candidates,:2]
        if np.linalg.eigvalsh(np.cov(xy,rowvar=False)).min()<.025:continue
        fitted=np.linalg.lstsq(seed_design[candidates],seeds[candidates,2],rcond=None)[0]
        deviation=seeds[candidates,2]-seed_design[candidates]@fitted
        if (math.hypot(*fitted[:2])<=math.tan(math.radians(config.max_slope_deg)) and
            np.sqrt(np.mean(deviation**2))<=config.ground_tolerance_m/2):
            local_planes[i]=fitted
    nearest=tree.query(local[:,:2],k=1)[1]
    residual=local[:,2]-np.sum(design*local_planes[nearest],axis=1)
    ground_local=np.abs(residual)<=config.ground_tolerance_m
    ground=zero.copy();obstacles=zero.copy()
    ground[indices]=ground_local
    obstacles[indices]=(residual>=config.obstacle_height_m)&(residual<=config.max_obstacle_height_m)
    unknown=eligible&~ground&~obstacles
    return GroundResult(True,'ok',ground,obstacles,unknown,tuple(map(float,plane)),float(ground_local.mean()),
                        float(np.sqrt(np.mean(residual[ground_local]**2))))
