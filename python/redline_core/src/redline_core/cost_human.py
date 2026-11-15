"""Human walking speed, metabolic cost and planning-edge cost (proje.md §7.2).

Every parameter is a SCENARIO assumption loaded from config/suit.yaml and
config/crew.yaml (see :mod:`redline_core.params`). Inputs are SI; grades are
rise/run, Pandolf grades are percent, angles in layers are degrees.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from numba import njit

from .grid import NEIGHBORS16, Grid

# CellState.msg codes.
UNOBSERVED = 0
DETECTED = 1
NOT_DETECTED_LIMITED = 2

_M_O2_KG_MOL = 31.9988e-3
_M_CO2_KG_MOL = 44.0095e-3

REQUIRED_LAYERS = ("z_m", "slope_deg", "slope_sigma_deg", "state", "relief_m", "wall_slope_deg")


def _check_positive(owner: object, *names: str, allow_zero: bool = False) -> None:
    for name in names:
        value = getattr(owner, name)
        if not (math.isfinite(value) and (value >= 0 if allow_zero else value > 0)):
            raise ValueError(f"{type(owner).__name__}.{name} must be {'>= 0' if allow_zero else '> 0'} and finite")


@dataclass(frozen=True)
class WalkModel:
    """Speed, ban and terrain parameters shared by the whole crew."""

    g_mars_m_s2: float = 3.721
    g_earth_m_s2: float = 9.80665
    leg_length_m: float = 0.9
    tobler_peak_kmh: float = 6.0
    tobler_decay: float = 3.5
    tobler_offset: float = 0.05
    pandolf_beta: float = 0.7
    downhill_kd: float = 0.3
    eta_default: float = 1.0
    slope_max_deg: float = 25.0
    slope_z: float = 1.645
    wall_relief_m: float = 0.8
    wall_slope_deg: float = 30.0
    speed_factor_unobserved: float = 0.7
    sigma_factor_unobserved: float = 1.5
    speed_factor_limited: float = 0.85
    sigma_factor_limited: float = 1.0
    rock_swath_m: float = 0.6
    rock_d_star_m: float = 0.5
    rock_detour_s: float | None = None  # λ: no spec value; must be set before a rock layer is used

    def __post_init__(self) -> None:
        _check_positive(
            self, "g_mars_m_s2", "g_earth_m_s2", "leg_length_m", "tobler_peak_kmh", "tobler_decay",
            "pandolf_beta", "eta_default", "slope_max_deg", "wall_relief_m", "wall_slope_deg",
            "speed_factor_unobserved", "sigma_factor_unobserved", "speed_factor_limited",
            "sigma_factor_limited", "rock_swath_m", "rock_d_star_m",
        )
        _check_positive(self, "tobler_offset", "downhill_kd", "slope_z", allow_zero=True)
        for name in ("speed_factor_unobserved", "speed_factor_limited"):
            if getattr(self, name) > 1.0:
                raise ValueError(f"WalkModel.{name} must be in (0, 1]")
        if self.rock_detour_s is not None and not (math.isfinite(self.rock_detour_s) and self.rock_detour_s >= 0):
            raise ValueError("WalkModel.rock_detour_s must be None or >= 0")

    @property
    def gravity_ratio(self) -> float:
        return self.g_mars_m_s2 / self.g_earth_m_s2

    @property
    def gravity_scale(self) -> float:
        """Pandolf standing/kinetic scale s = (g_M/g_E)^β."""
        return self.gravity_ratio**self.pandolf_beta

    @property
    def peak_speed_m_s(self) -> float:
        return math.sqrt(self.gravity_ratio) * self.tobler_peak_kmh / 3.6

    @property
    def walk_run_speed_m_s(self) -> float:
        return math.sqrt(0.5 * self.g_mars_m_s2 * self.leg_length_m)


@dataclass(frozen=True)
class CrewMember:
    crew_id: str
    body_mass_kg: float  # W
    load_mass_kg: float  # L: carried load + suit
    theta: float = 1.0  # personal metabolic multiplier

    def __post_init__(self) -> None:
        _check_positive(self, "body_mass_kg", "theta")
        _check_positive(self, "load_mass_kg", allow_zero=True)


@dataclass(frozen=True)
class SuitModel:
    # Suit cost not explained by weight, proportional to walking speed (constant per metre):
    # least-squares fit through the origin of EWT 3/8 g Table 5 (14.9, 18.8, 21.6 ml/kg/min at
    # 1.245, 1.375, 1.515 m/s; NASA/TP-2009-214796). Slower speeds are extrapolated. D010.
    suit_vo2_per_speed: float = 13.4  # ml O2 / kg body / min per m/s
    # Station work above standing: EWT 1/6 g suit cost ~8 ml/kg/min at all speeds, IST load carry
    # 7.1-10.0 (NASA/TP-2010-216125); a lunar value used at Mars, so likely low. D010.
    station_task_vo2_ml_kg_min: float = 8.0
    watts_per_l_min_o2: float = 335.0
    o2_g_per_wh: float = 0.256
    respiratory_quotient: float = 0.85
    evaporative_fraction: float = 0.8  # (1 - 0.2)
    latent_heat_j_kg: float = 2.45e6
    battery_base_w: float = 60.0
    battery_k: float = 0.05

    def __post_init__(self) -> None:
        _check_positive(
            self, "watts_per_l_min_o2", "o2_g_per_wh", "respiratory_quotient", "latent_heat_j_kg"
        )
        _check_positive(
            self, "suit_vo2_per_speed", "station_task_vo2_ml_kg_min", "evaporative_fraction", "battery_base_w",
            "battery_k", allow_zero=True,
        )


@dataclass(frozen=True)
class Consumables:
    o2_kg: np.ndarray | float
    co2_kg: np.ndarray | float
    water_kg: np.ndarray | float
    battery_wh: np.ndarray | float

    def scaled(self, factor) -> "Consumables":
        return Consumables(
            self.o2_kg * factor, self.co2_kg * factor, self.water_kg * factor, self.battery_wh * factor
        )


@dataclass(frozen=True)
class EdgeCost:
    time_s: float
    var_s2: float
    energy_per_kg_j: float  # ∫ η·(s·1.5V² + 0.35·g_r·V·G⁺ + k_d·0.35·g_r·V·G⁻) dt
    distance_m: float  # horizontal path length (the suit cost is per metre, D010)


def walking_speed(grade, model: WalkModel):
    """Tobler × Froude speed in m/s, capped at the walk-run transition."""
    g = np.asarray(grade, dtype=float)
    v = model.peak_speed_m_s * np.exp(-model.tobler_decay * np.abs(g + model.tobler_offset))
    v = np.minimum(v, model.walk_run_speed_m_s)
    return float(v) if v.ndim == 0 else v


def standing_power_w(crew: CrewMember, model: WalkModel) -> float:
    w, load = crew.body_mass_kg, crew.load_mass_kg
    return model.gravity_scale * (1.5 * w + 2.0 * (w + load) * (load / w) ** 2)


def walking_power_per_kg(speed_m_s, grade_percent, eta, model: WalkModel):
    """Pandolf walking term per kg of (W+L), already multiplied by η."""
    v = np.asarray(speed_m_s, dtype=float)
    g = np.asarray(grade_percent, dtype=float)
    up, down = np.maximum(g, 0.0), np.maximum(-g, 0.0)
    gr = model.gravity_ratio
    return eta * (
        model.gravity_scale * 1.5 * v * v + 0.35 * gr * v * up + model.downhill_kd * 0.35 * gr * v * down
    )


def suit_energy_per_m_j(crew: CrewMember, suit: SuitModel) -> float:
    """Suit non-weight cost per metre walked (J/m); power = this x speed (D010)."""
    return suit.watts_per_l_min_o2 * suit.suit_vo2_per_speed * 1e-3 * crew.body_mass_kg


def suit_power_w(crew: CrewMember, suit: SuitModel, speed_m_s):
    """Suit non-weight power at a walking speed; zero when standing (D010)."""
    p = suit_energy_per_m_j(crew, suit) * np.asarray(speed_m_s, dtype=float)
    return float(p) if np.ndim(p) == 0 else p


def station_power_w(crew: CrewMember, suit: SuitModel, model: WalkModel) -> float:
    """Station work: theta x standing plus the suited task increment (D010)."""
    task = suit.watts_per_l_min_o2 * suit.station_task_vo2_ml_kg_min * 1e-3 * crew.body_mass_kg
    return crew.theta * standing_power_w(crew, model) + task


def metabolic_power(speed_m_s, grade_percent, eta, crew: CrewMember, suit: SuitModel, model: WalkModel):
    bracket = standing_power_w(crew, model) + (crew.body_mass_kg + crew.load_mass_kg) * walking_power_per_kg(
        speed_m_s, grade_percent, eta, model
    )
    m = crew.theta * bracket + suit_power_w(crew, suit, speed_m_s)
    return float(m) if np.ndim(m) == 0 else m


def consumables_from_energy(energy_j, duration_s, suit: SuitModel) -> Consumables:
    """O₂, CO₂, cooling water and battery for a metabolic energy over a duration."""
    energy = np.asarray(energy_j, dtype=float)
    duration = np.asarray(duration_s, dtype=float)
    o2 = suit.o2_g_per_wh * 1e-3 * energy / 3600.0
    co2 = suit.respiratory_quotient * (_M_CO2_KG_MOL / _M_O2_KG_MOL) * o2
    water = suit.evaporative_fraction * energy / suit.latent_heat_j_kg
    battery = (suit.battery_base_w * duration + suit.battery_k * energy) / 3600.0

    def out(a):
        return float(a) if np.ndim(a) == 0 else a

    return Consumables(out(o2), out(co2), out(water), out(battery))


def path_metabolic_energy_j(time_s, energy_per_kg_j, distance_m, crew: CrewMember, suit: SuitModel,
                            model: WalkModel):
    """Exact for any θ, W, L: E = θ·(standing·T + (W+L)·F) + e_suit·D (D010)."""
    t = np.asarray(time_s, dtype=float)
    f = np.asarray(energy_per_kg_j, dtype=float)
    d = np.asarray(distance_m, dtype=float)
    bracket = standing_power_w(crew, model) * t + (crew.body_mass_kg + crew.load_mass_kg) * f
    return crew.theta * bracket + suit_energy_per_m_j(crew, suit) * d


def path_consumables(time_s, energy_per_kg_j, distance_m, crew: CrewMember, suit: SuitModel,
                     model: WalkModel) -> Consumables:
    energy = path_metabolic_energy_j(time_s, energy_per_kg_j, distance_m, crew, suit, model)
    return consumables_from_energy(energy, time_s, suit)


# --- numba edge kernel --------------------------------------------------------------

def _edge_tables():
    n = len(NEIGHBORS16)
    offsets = np.array(NEIGHBORS16, dtype=np.int64)
    part_n = np.zeros(n, dtype=np.int64)
    part_d = np.zeros((n, 4, 2), dtype=np.int64)
    part_w = np.zeros((n, 4), dtype=np.float64)
    block_n = np.zeros(n, dtype=np.int64)
    block_d = np.zeros((n, 4, 2), dtype=np.int64)
    for o, (dy, dx) in enumerate(NEIGHBORS16):
        if max(abs(dy), abs(dx)) == 1:
            parts = [((0, 0), 0.5), ((dy, dx), 0.5)]
            # A diagonal step touches the corner it passes: both side cells must be free.
            blockers = [(0, 0), (dy, dx)] + ([(dy, 0), (0, dx)] if dy and dx else [])
        else:
            # A knight segment crosses four cells, a quarter of its length in each.
            mid = [(0, dx // 2), (dy, dx // 2)] if abs(dx) == 2 else [(dy // 2, 0), (dy // 2, dx)]
            cells = [(0, 0), *mid, (dy, dx)]
            parts = [(cell, 0.25) for cell in cells]
            blockers = cells
        part_n[o] = len(parts)
        for p, (cell, weight) in enumerate(parts):
            part_d[o, p] = cell
            part_w[o, p] = weight
        block_n[o] = len(blockers)
        for b, cell in enumerate(blockers):
            block_d[o, b] = cell
    return offsets, part_n, part_d, part_w, block_n, block_d


OFFSETS, PART_N, PART_D, PART_W, BLOCK_N, BLOCK_D = _edge_tables()

# Packed model parameters for the kernel.
_P_RES, _P_VPEAK, _P_DECAY, _P_OFFSET, _P_VWR, _P_S, _P_GR, _P_KD, _P_SMAX, _P_SZ, _P_ROCK_L, _P_SWATH = range(12)


@njit(cache=True)
def _speed(grade, p):
    v = p[_P_VPEAK] * math.exp(-p[_P_DECAY] * abs(grade + p[_P_OFFSET]))
    return v if v < p[_P_VWR] else p[_P_VWR]


@njit(cache=True)
def _edge(start, o, width, z, banned, speed_f, sigma_f, sigma_rad, eta, rock, p,
          offsets, part_n, part_d, part_w, block_n, block_d):
    """(ok, time_s, sigma_s, energy_per_kg, distance_m) for the edge leaving `start` along offset o."""
    sy = start // width
    sx = start - sy * width
    for b in range(block_n[o]):
        if banned[(sy + block_d[o, b, 0]) * width + sx + block_d[o, b, 1]]:
            return False, 0.0, 0.0, 0.0, 0.0
    dy = offsets[o, 0]
    dx = offsets[o, 1]
    end = (sy + dy) * width + sx + dx
    length = p[_P_RES] * math.sqrt(dy * dy + dx * dx)
    grade = (z[end] - z[start]) / length
    sigma_max = 0.0
    for k in range(part_n[o]):
        c = (sy + part_d[o, k, 0]) * width + sx + part_d[o, k, 1]
        if sigma_rad[c] > sigma_max:
            sigma_max = sigma_rad[c]
    if math.degrees(math.atan(abs(grade))) + p[_P_SZ] * math.degrees(sigma_max) > p[_P_SMAX]:
        return False, 0.0, 0.0, 0.0, 0.0
    v = _speed(grade, p)
    g_pct = 100.0 * grade
    g_up = g_pct if g_pct > 0.0 else 0.0
    g_down = -g_pct if g_pct < 0.0 else 0.0
    t = 0.0
    sigma = 0.0
    energy = 0.0
    rock_density = 0.0
    for k in range(part_n[o]):
        c = (sy + part_d[o, k, 0]) * width + sx + part_d[o, k, 1]
        seg = part_w[o, k] * length
        vc = v * speed_f[c]
        tc = seg / vc
        s_grade = sigma_rad[c] * (1.0 + grade * grade)  # d(tan)/dθ = sec²θ
        t_plus = seg / (_speed(grade + s_grade, p) * speed_f[c])
        t_minus = seg / (_speed(grade - s_grade, p) * speed_f[c])
        dev = max(abs(t_plus - tc), abs(t_minus - tc))  # one-sided: robust at the Tobler kink
        sigma += dev * sigma_f[c]
        energy += eta[c] * (
            p[_P_S] * 1.5 * vc * vc + 0.35 * p[_P_GR] * vc * g_up + p[_P_KD] * 0.35 * p[_P_GR] * vc * g_down
        ) * tc
        t += tc
        rock_density += part_w[o, k] * rock[c]
    detour = p[_P_ROCK_L] * rock_density * p[_P_SWATH] * length
    distance = length
    if detour > 0.0:
        energy += energy / t * detour
        distance += length / t * detour  # the detour is walked at the edge's mean speed
        t += detour
    return True, t, sigma, energy, distance


@dataclass(frozen=True, eq=False)
class PreparedTerrain:
    height: int
    width: int
    resolution_m: float
    origin_xy: tuple[float, float]
    z: np.ndarray
    banned: np.ndarray
    speed_factor: np.ndarray
    sigma_factor: np.ndarray
    sigma_slope_rad: np.ndarray
    eta: np.ndarray
    rock_n: np.ndarray
    params: np.ndarray
    rock_term_applied: bool
    sigma_fallback_cells: int
    notes: tuple[str, ...] = field(default=())

    @property
    def banned_mask(self) -> np.ndarray:
        return self.banned.reshape(self.height, self.width)

    def kernel_args(self):
        return (self.z, self.banned, self.speed_factor, self.sigma_factor, self.sigma_slope_rad,
                self.eta, self.rock_n, self.params, OFFSETS, PART_N, PART_D, PART_W, BLOCK_N, BLOCK_D)

    def flat_index(self, cell: tuple[int, int]) -> int:
        iy, ix = cell
        if not (0 <= iy < self.height and 0 <= ix < self.width):
            raise ValueError(f"cell {cell} is outside the grid")
        return iy * self.width + ix


def prepare_terrain(grid: Grid, model: WalkModel, *, sigma_fallback_deg: float | None = None) -> PreparedTerrain:
    """Validate layers, apply ban rules and observation-state factors."""
    missing = [name for name in REQUIRED_LAYERS if name not in grid.layers]
    if missing:
        raise ValueError(f"grid is missing required layers {missing}")

    def flat(name):
        return np.ascontiguousarray(np.asarray(grid.layers[name], dtype=float).ravel())

    z, slope, sigma = flat("z_m"), flat("slope_deg"), flat("slope_sigma_deg")
    relief, wall = flat("relief_m"), flat("wall_slope_deg")
    state = np.asarray(grid.layers["state"]).ravel()
    if not np.isin(state, (UNOBSERVED, DETECTED, NOT_DETECTED_LIMITED)).all():
        raise ValueError("state codes must be CellState UNOBSERVED/DETECTED/NOT_DETECTED_LIMITED")

    notes = []
    sigma_missing = ~np.isfinite(sigma)
    if sigma_missing.any():
        if sigma_fallback_deg is None:
            raise ValueError(
                f"slope_sigma_deg is missing in {int(sigma_missing.sum())} cells; missing sigma is never "
                "treated as zero: pass an explicit sigma_fallback_deg"
            )
        if not (math.isfinite(sigma_fallback_deg) and sigma_fallback_deg >= 0):
            raise ValueError("sigma_fallback_deg must be finite and >= 0")
        sigma = np.where(sigma_missing, sigma_fallback_deg, sigma)
        notes.append(f"sigma fallback {sigma_fallback_deg} deg in {int(sigma_missing.sum())} cells")
    if (sigma < 0).any():
        raise ValueError("slope_sigma_deg must be >= 0")

    banned = ~(np.isfinite(z) & np.isfinite(slope) & np.isfinite(relief) & np.isfinite(wall))
    with np.errstate(invalid="ignore"):
        banned |= np.abs(slope) + model.slope_z * sigma > model.slope_max_deg
        banned |= (relief > model.wall_relief_m) & (wall > model.wall_slope_deg)
    if "blocked" in grid.layers:  # D015: observed obstacles (cell_observation v2)
        banned |= np.asarray(grid.layers["blocked"], dtype=bool).ravel()

    speed = np.select(
        [state == UNOBSERVED, state == NOT_DETECTED_LIMITED],
        [model.speed_factor_unobserved, model.speed_factor_limited],
        1.0,
    ).astype(float)
    sigma_factor = np.select(
        [state == UNOBSERVED, state == NOT_DETECTED_LIMITED],
        [model.sigma_factor_unobserved, model.sigma_factor_limited],
        1.0,
    ).astype(float)

    if "eta" in grid.layers:
        eta = flat("eta")
        if not (np.isfinite(eta) & (eta > 0)).all():
            raise ValueError("eta layer must be finite and > 0")
    else:
        eta = np.full(z.size, model.eta_default)

    rock_applied = "rock_n_ge_per_m2" in grid.layers
    if rock_applied:
        if model.rock_detour_s is None:
            raise ValueError("a rock layer needs WalkModel.rock_detour_s (SCENARIO λ, no spec value)")
        rock = flat("rock_n_ge_per_m2")
        if not (np.isfinite(rock) & (rock >= 0)).all():
            raise ValueError("rock_n_ge_per_m2 must be finite and >= 0")
    else:
        rock = np.zeros(z.size)
        notes.append("no rock layer: rock risk term not applied")

    params = np.zeros(12)
    params[_P_RES] = grid.resolution_m
    params[_P_VPEAK] = model.peak_speed_m_s
    params[_P_DECAY] = model.tobler_decay
    params[_P_OFFSET] = model.tobler_offset
    params[_P_VWR] = model.walk_run_speed_m_s
    params[_P_S] = model.gravity_scale
    params[_P_GR] = model.gravity_ratio
    params[_P_KD] = model.downhill_kd
    params[_P_SMAX] = model.slope_max_deg
    params[_P_SZ] = model.slope_z
    params[_P_ROCK_L] = model.rock_detour_s if rock_applied else 0.0
    params[_P_SWATH] = model.rock_swath_m

    return PreparedTerrain(
        height=grid.height,
        width=grid.width,
        resolution_m=grid.resolution_m,
        origin_xy=tuple(grid.origin_xy),
        z=np.where(np.isfinite(z), z, 0.0),  # banned cells never enter an edge
        banned=np.ascontiguousarray(banned),
        speed_factor=speed,
        sigma_factor=sigma_factor,
        sigma_slope_rad=np.radians(sigma),
        eta=eta,
        rock_n=rock,
        params=params,
        rock_term_applied=rock_applied,
        sigma_fallback_cells=int(sigma_missing.sum()),
        notes=tuple(notes),
    )


_OFFSET_INDEX = {offset: i for i, offset in enumerate(NEIGHBORS16)}


def edge_cost(terrain: PreparedTerrain, start: tuple[int, int], offset: tuple[int, int]) -> EdgeCost | None:
    """Cost of the directed edge start -> start+offset, or None when it is not walkable."""
    o = _OFFSET_INDEX.get(tuple(offset))
    if o is None:
        raise ValueError(f"offset {offset} is not a 16-neighbourhood offset")
    a = terrain.flat_index(start)
    terrain.flat_index((start[0] + offset[0], start[1] + offset[1]))
    ok, t, sigma, energy, distance = _edge(a, o, terrain.width, *terrain.kernel_args())
    return EdgeCost(t, sigma * sigma, energy, distance) if ok else None
