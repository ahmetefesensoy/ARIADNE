"""Return margin, limiting consumable and red/yellow line polygons (proje.md §7.6).

Margins are seconds internally (SI); `margin_min` is the output-layer view.
Codes follow MarginField.msg. Cells with no walkable return path have NaN margin
and LIM_NONE (255, not a MarginField constant: consumers must treat it as
"unreachable"). In SEP mode, cells beyond the shelter limit get -inf and
LIM_SHELTER.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from skimage import measure

from .cost_human import CrewMember, SuitModel, WalkModel, consumables_from_energy
from .walkback import WalkbackField

LIM_O2 = 0
LIM_CO2 = 1
LIM_WATER = 2
LIM_BATTERY = 3
LIM_DAYLIGHT = 4
LIM_SHELTER = 5
LIM_NONE = 255
CONSUMABLE_CODES = (LIM_O2, LIM_CO2, LIM_WATER, LIM_BATTERY)
# Relative margin difference treated as a tie. Live inputs arrive through float32
# ROS fields (Consumables), so ties are judged at float32-level precision (D009;
# D008 used 1e-9). 1e-5 of a 60 min margin is 36 ms.
TIE_REL_TOL = 1e-5


@dataclass(frozen=True)
class Resources:
    o2_kg: float
    co2_capacity_kg: float
    water_kg: float
    battery_wh: float


@dataclass(frozen=True)
class Rates:
    """Current consumption rates (SI)."""

    o2_kg_s: float
    co2_kg_s: float
    water_kg_s: float
    battery_w: float

    @classmethod
    def from_metabolic_power(cls, power_w: float, suit: SuitModel) -> "Rates":
        per_second = consumables_from_energy(power_w, 1.0, suit)
        return cls(per_second.o2_kg, per_second.co2_kg, per_second.water_kg, per_second.battery_wh * 3600.0)


@dataclass(frozen=True, eq=False)
class MarginField:
    margin_s: np.ndarray
    limiting: np.ndarray

    @property
    def margin_min(self) -> np.ndarray:
        return self.margin_s / 60.0


@dataclass(frozen=True, eq=False)
class CrewMargin:
    field: MarginField
    limiting_crew: np.ndarray  # index into crew_ids
    crew_ids: tuple[str, ...]


def margins(
    needs: Mapping[int, np.ndarray],
    available: Mapping[int, float],
    rates_per_s: Mapping[int, float],
    *,
    time_need_s: np.ndarray | None = None,
    daylight_budget_s: float | None = None,
    shelter_time_s: np.ndarray | None = None,
    shelter_max_s: float | None = None,
) -> MarginField:
    """m_j = (R_j - R_rez,j - W_j,ε) / ṙ_j; margin = min_j m_j (and daylight)."""
    codes = sorted(needs)
    if not codes or set(codes) - set(CONSUMABLE_CODES):
        raise ValueError("needs must be keyed by consumable LIM_* codes")
    if set(available) != set(codes) or set(rates_per_s) != set(codes):
        raise ValueError("needs, available and rates must name the same consumables")
    for code in codes:
        rate = rates_per_s[code]
        if not (np.isfinite(rate) and rate > 0):
            raise ValueError(f"consumption rate for code {code} must be positive and finite")
        if not np.isfinite(available[code]):
            raise ValueError(f"available amount for code {code} must be finite")

    need_arrays = [np.asarray(needs[c], dtype=float) for c in codes]
    unreachable = np.zeros(need_arrays[0].shape, dtype=bool)
    candidates, labels = [], []
    for code, need in zip(codes, need_arrays):
        unreachable |= np.isinf(need)
        candidates.append((available[code] - need) / rates_per_s[code])
        labels.append(code)
    if daylight_budget_s is not None:
        if time_need_s is None:
            raise ValueError("a daylight budget needs the risk-adjusted return time")
        time_need = np.asarray(time_need_s, dtype=float)
        unreachable |= np.isinf(time_need)
        candidates.append(daylight_budget_s - time_need)
        labels.append(LIM_DAYLIGHT)

    raw = np.stack(candidates)
    stack = np.where(np.isnan(raw), np.inf, raw)
    margin = stack.min(axis=0)
    # Consumables that run out together (within float noise) resolve to the lowest code.
    tolerance = np.where(np.isfinite(margin), TIE_REL_TOL * np.maximum(1.0, np.abs(margin)), 0.0)
    index = np.argmax(stack <= margin + tolerance, axis=0)
    limiting = np.asarray(labels, dtype=np.uint8)[index]

    if shelter_time_s is not None:
        if shelter_max_s is None:
            raise ValueError("SEP mode needs shelter_max_s")
        too_far = np.asarray(shelter_time_s, dtype=float) > shelter_max_s
        margin = np.where(too_far, -np.inf, margin)
        limiting = np.where(too_far, LIM_SHELTER, limiting).astype(np.uint8)

    margin = np.where(unreachable, np.nan, margin)
    limiting = np.where(unreachable, LIM_NONE, limiting).astype(np.uint8)
    return MarginField(margin, limiting)


def margin_for_crew(
    field: WalkbackField,
    crew: CrewMember,
    suit: SuitModel,
    model: WalkModel,
    remaining: Resources,
    reserve: Resources,
    rates: Rates,
    *,
    z: float = 1.645,
    sigma_theta: float = 0.2,
    daylight_budget_s: float | None = None,
    shelter_time_s: np.ndarray | None = None,
    shelter_max_s: float | None = None,
) -> MarginField:
    need = field.consumables(crew, suit, model, risk=True, z=z, sigma_theta=sigma_theta)
    needs = {LIM_O2: need.o2_kg, LIM_CO2: need.co2_kg, LIM_WATER: need.water_kg, LIM_BATTERY: need.battery_wh}
    available = {
        LIM_O2: remaining.o2_kg - reserve.o2_kg,
        LIM_CO2: remaining.co2_capacity_kg - reserve.co2_capacity_kg,
        LIM_WATER: remaining.water_kg - reserve.water_kg,
        LIM_BATTERY: remaining.battery_wh - reserve.battery_wh,
    }
    per_second = {
        LIM_O2: rates.o2_kg_s,
        LIM_CO2: rates.co2_kg_s,
        LIM_WATER: rates.water_kg_s,
        LIM_BATTERY: rates.battery_w / 3600.0,
    }
    return margins(
        needs,
        available,
        per_second,
        time_need_s=field.time_eps_s(z, sigma_theta) if daylight_budget_s is not None else None,
        daylight_budget_s=daylight_budget_s,
        shelter_time_s=shelter_time_s,
        shelter_max_s=shelter_max_s,
    )


def combine_crew(fields: Mapping[str, MarginField]) -> CrewMargin:
    """The displayed line follows the worse crew member in every cell (proje.md §7.6)."""
    if not fields:
        raise ValueError("at least one crew margin is required")
    crew_ids = tuple(fields)
    stack = np.stack([fields[c].margin_s for c in crew_ids])
    index = np.argmin(np.where(np.isnan(stack), -np.inf, stack), axis=0)
    margin = np.take_along_axis(stack, index[None], axis=0)[0]
    limiting = np.take_along_axis(np.stack([fields[c].limiting for c in crew_ids]), index[None], axis=0)[0]
    return CrewMargin(MarginField(margin, limiting), index, crew_ids)


def _signed_area(ring: np.ndarray) -> float:
    x, y = ring[:, 0], ring[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def region_contours(margin_s: np.ndarray, origin_xy, resolution_m: float, level_s: float,
                    min_hole_cells: float = 0.0) -> list[np.ndarray]:
    """Closed rings (map-frame x, y) bounding cells with margin >= level.

    Outer boundaries are counter-clockwise and holes clockwise. Unreachable (NaN)
    and SEP-excluded (-inf) cells lie outside every region. With `min_hole_cells`,
    enclosed below-level pockets smaller than that many cells are not outlined
    (display geometry only; see :mod:`redline_core.polyline`).
    """
    from .polyline import fill_small_holes

    m = np.asarray(margin_s, dtype=float)
    outside = level_s - 1.0
    finite_max = np.nanmax(np.where(np.isfinite(m), m, np.nan)) if np.isfinite(m).any() else level_s
    inside = max(finite_max, level_s) + 1.0
    work = np.where(np.isfinite(m), m, np.where(m == np.inf, inside, outside))
    if min_hole_cells > 0:
        work = fill_small_holes(work, level_s, min_hole_cells, inside)
    padded = np.pad(work, 1, constant_values=outside)
    raw = measure.find_contours(padded, level_s, fully_connected="high", positive_orientation="high")
    x0, y0 = origin_xy
    rings = []
    for contour in raw:
        rows, cols = contour[:, 0] - 1.0, contour[:, 1] - 1.0
        ring = np.column_stack([x0 + (cols + 0.5) * resolution_m, y0 + (rows + 0.5) * resolution_m])
        if not np.allclose(ring[0], ring[-1]):
            ring = np.vstack([ring, ring[:1]])
        rings.append(ring)
    if rings:
        areas = [_signed_area(r) for r in rings]
        # The largest ring is always an outer boundary (holes lie inside an outer ring);
        # find_contours orients consistently, so one check fixes the whole set.
        if areas[int(np.argmax(np.abs(areas)))] < 0:
            rings = [r[::-1].copy() for r in rings]
    return rings
