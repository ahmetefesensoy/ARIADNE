"""Bounded translation-only empirical DEM alignment, in metres.

The gradient/residual relation follows the translation principle in Nuth & Kaab
(2011), https://doi.org/10.5194/tc-5-271-2011. This small implementation is not
their full workflow: it does not estimate tilt, sensor bias or absolute geodetic
accuracy. Stable common terrain, CRS/grid/vertical compatibility and masks must
be established by the caller. Held-out cells measure internal agreement only.
"""
from __future__ import annotations

import math

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _array(values: ArrayLike) -> NDArray[np.float64]:
    if np.iscomplexobj(values):
        raise ValueError("DEM elevations must be real metres")
    data = np.ma.asarray(values, dtype=np.float64).filled(np.nan)
    if data.ndim != 2 or min(data.shape) < 3 or data.size > 25_000_000:
        raise ValueError("Expected a bounded 2-D DEM, at least 3x3, at most 25M cells")
    return np.where(np.isfinite(data), data, np.nan)


def _positive(value: float, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return float(value)


def _sample(data, rows, cols):
    """Bilinear samples and derivatives per row/column pixel; no mask bridging."""
    r0, c0 = np.floor(rows).astype(int), np.floor(cols).astype(int)
    valid = (r0 >= 0) & (c0 >= 0) & (r0 + 1 < data.shape[0]) & (c0 + 1 < data.shape[1])
    r0, c0 = np.clip(r0, 0, data.shape[0] - 2), np.clip(c0, 0, data.shape[1] - 2)
    a, b = data[r0, c0], data[r0, c0 + 1]
    c, d = data[r0 + 1, c0], data[r0 + 1, c0 + 1]
    valid &= np.isfinite(a) & np.isfinite(b) & np.isfinite(c) & np.isfinite(d)
    fr, fc = rows - r0, cols - c0
    value = (1 - fr) * ((1 - fc) * a + fc * b) + fr * ((1 - fc) * c + fc * d)
    dr = (1 - fc) * (c - a) + fc * (d - b)
    dc = (1 - fr) * (b - a) + fr * (d - c)
    return np.where(valid, value, np.nan), dr, dc


def shift_array(
    reference: ArrayLike, dx_m: float, dy_m: float, resolution_m: float
) -> NDArray[np.float64]:
    """Translate content east by dx and north by dy on a north-up square grid.

    Output[r,c] samples reference[r+dy/res,c-dx/res]. No vertical correction is
    applied here. Bilinear support containing missing cells and exterior samples
    stays NaN. Chunked rows limit temporary memory even for a 1 m product.
    """
    data = _array(reference)
    resolution = _positive(resolution_m, "resolution_m")
    if not all(math.isfinite(value) for value in (dx_m, dy_m)):
        raise ValueError("Translations must be finite metres")
    result = np.full(data.shape, np.nan)
    for start in range(0, data.shape[0], 128):
        stop = min(start + 128, data.shape[0])
        rows, cols = np.meshgrid(np.arange(start, stop), np.arange(data.shape[1]), indexing="ij")
        values, _dr, _dc = _sample(data, rows + dy_m / resolution, cols - dx_m / resolution)
        result[start:stop] = values
    return result


def _metrics(values):
    median = float(np.median(values))
    return {
        "count": int(values.size),
        "rmse_m": float(np.sqrt(np.mean(values * values))),
        "median_m": median,
        "nmad_m": float(1.4826 * np.median(np.abs(values - median))),
    }


def register(
    primary: ArrayLike,
    reference: ArrayLike,
    resolution_m: float,
    max_shift_m: float = 20,
    *,
    grids_verified: bool = False,
    max_samples: int = 12000,
    max_iterations: int = 40,
    min_overlap: int = 100,
    tolerance_m: float = 0.002,
) -> dict:
    """Fit reference translation plus median vertical bias to stable terrain.

    Require ``grids_verified=True`` ONLY after verifying the same grid affine,
    CRS, units, resolution, vertical reference and stable-terrain masks. A rigid
    horizontal offset is what this function estimates, not an initial CRS fix.
    On rejected/ambiguous fits this raises ValueError, never returns success.

    At most max_samples deterministic cells are split into disjoint training and
    holdout sets. A coarse bounded search initializes robust gradient refinement.
    Boundary optima, low-texture/one-dimensional terrain, nonconvergence and
    worsening heldout agreement are rejected. max_shift_m bounds each axis.

    ``aligned_reference`` includes the vertical offset added to the shifted
    reference. ``vertical_offset_removed_m`` is median(primary-shifted_ref),
    i.e. the bias removed from the difference, not an independent datum estimate.
    """
    if grids_verified is not True:
        raise ValueError("Verify common grid, CRS, vertical reference and stable terrain first")
    first, second = _array(primary), _array(reference)
    if first.shape != second.shape:
        raise ValueError("Primary and reference must occupy the same grid shape")
    if first.size > 4_000_000:
        raise ValueError("Fit on a verified coarser grid, at most 4M cells")
    resolution = _positive(resolution_m, "resolution_m")
    bound = _positive(max_shift_m, "max_shift_m")
    tolerance = _positive(tolerance_m, "tolerance_m")
    for value, name, minimum, maximum in (
        (max_samples, "max_samples", 200, 100000),
        (max_iterations, "max_iterations", 1, 200),
        (min_overlap, "min_overlap", 30, 100000),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    margin = math.ceil(bound / resolution) + 2
    height, width = first.shape
    if min(height, width) <= 2 * margin + 4:
        raise ValueError("Insufficient interior extent for the requested shift budget")
    stride = max(1, math.ceil(math.sqrt((height - 2 * margin) * (width - 2 * margin) / max_samples)))
    rows, cols = np.meshgrid(
        np.arange(margin, height - margin, stride),
        np.arange(margin, width - margin, stride), indexing="ij",
    )
    rows, cols = rows.ravel(), cols.ravel()
    # Fixed common support for every candidate shift avoids comparing different
    # subsets to improve a score artificially. Integral image tests the entire
    # reference square inside the search budget, including bilinear neighbours.
    invalid = np.pad(np.cumsum(np.cumsum(~np.isfinite(second), axis=0), axis=1), ((1, 0), (1, 0)))
    low_r, high_r = rows - margin, rows + margin + 1
    low_c, high_c = cols - margin, cols + margin + 1
    bad = invalid[high_r, high_c] - invalid[low_r, high_c] - invalid[high_r, low_c] + invalid[low_r, low_c]
    keep = (bad == 0) & np.isfinite(first[rows, cols])
    rows, cols = rows[keep].astype(float), cols[keep].astype(float)
    if rows.size < min_overlap:
        raise ValueError("Insufficient common valid terrain inside the full shift budget")
    # Deterministic interleaved holdout never participates in fit or seed choice.
    order = np.random.default_rng(1401126).permutation(rows.size)
    heldout = order[::5]
    train = np.delete(order, np.arange(0, order.size, 5))
    if train.size < 30 or heldout.size < 10:
        raise ValueError("Insufficient disjoint training and heldout cells")
    targets = first[rows.astype(int), cols.astype(int)]

    def evaluate(dx, dy, indices):
        samples, dr, dc = _sample(second, rows[indices] + dy / resolution, cols[indices] - dx / resolution)
        difference = targets[indices] - samples
        bias = float(np.median(difference))
        return difference - bias, bias, np.column_stack((-dc / resolution, dr / resolution))

    residual0, bias0, gradients = evaluate(0, 0, train)
    covariance = np.cov(gradients, rowvar=False)
    eigenvalues = np.linalg.eigvalsh(covariance)
    if eigenvalues[0] <= 1e-8 or eigenvalues[0] / eigenvalues[-1] < 1e-4:
        raise ValueError("Degenerate planar or insufficient two-dimensional terrain texture")

    # A fixed Huber threshold makes every candidate comparable. Re-estimating
    # its threshold per candidate changes the objective during optimization.
    huber_threshold = max(1e-5, 1.5 * 1.4826 * np.median(np.abs(residual0)))

    def score(residual):
        absolute = np.abs(residual)
        return float(np.mean(np.where(absolute <= huber_threshold,
            .5 * residual * residual,
            huber_threshold * (absolute - .5 * huber_threshold))))

    seeds = np.linspace(-bound, bound, 9)
    best = (score(residual0), 0.0, 0.0)
    for dx in seeds:
        for dy in seeds:
            residual, _bias, _gradient = evaluate(dx, dy, train)
            candidate = (score(residual), float(dx), float(dy))
            if candidate[0] < best[0]:
                best = candidate
    _, dx, dy = best
    converged = False
    for iteration in range(1, max_iterations + 1):
        residual, bias, gradients = evaluate(dx, dy, train)
        # Joint translation/intercept step; re-estimate the median intercept for
        # every candidate, rather than trusting a least-squares vertical datum.
        design = np.column_stack((gradients, np.ones(train.size)))
        weights = np.minimum(1.0, huber_threshold / np.maximum(np.abs(residual), 1e-12))
        delta, *_ = np.linalg.lstsq(design * np.sqrt(weights[:, None]), residual * np.sqrt(weights), rcond=None)
        if np.linalg.norm(delta[:2]) < tolerance:
            converged = True
            break
        previous = score(residual)
        accepted = False
        for fraction in (1, .5, .25, .125, .0625, .03125):
            nx, ny = dx + fraction * delta[0], dy + fraction * delta[1]
            if abs(nx) >= bound or abs(ny) >= bound:
                continue
            proposal, _bias, _gradients = evaluate(nx, ny, train)
            if score(proposal) < previous:
                dx, dy = float(nx), float(ny)
                accepted = True
                if np.linalg.norm(fraction * delta[:2]) < tolerance:
                    converged = True
                break
        if converged:
            break
        if not accepted:
            # Median intercept and bilinear cell boundaries are non-smooth.
            # Verify a bounded pattern-search neighbourhood before claiming
            # convergence; do not relax the requested metre tolerance.
            step = min(resolution / 2, bound / 4)
            while step >= tolerance:
                neighbour = (previous, dx, dy)
                for ox, oy in ((-step, 0), (step, 0), (0, -step), (0, step),
                               (-step, -step), (-step, step), (step, -step), (step, step)):
                    nx, ny = dx + ox, dy + oy
                    if abs(nx) >= bound or abs(ny) >= bound:
                        continue
                    candidate, _bias, _gradient = evaluate(nx, ny, train)
                    candidate_score = score(candidate)
                    if candidate_score < neighbour[0]:
                        neighbour = (candidate_score, nx, ny)
                if neighbour[0] < previous:
                    _score, dx, dy = neighbour
                    accepted = True
                    break
                step /= 2
            if not accepted:
                converged = True
                break
    if not converged:
        raise ValueError("Registration exceeded its iteration budget")
    if abs(dx) >= bound - tolerance or abs(dy) >= bound - tolerance:
        raise ValueError("Registration optimum reaches the shift budget boundary")
    training, bias, _gradients = evaluate(dx, dy, train)
    held_before, _held_bias, _ = evaluate(0, 0, heldout)
    # Holdout never estimates the fitted correction: use the TRAINING intercept.
    sampled, _dr, _dc = _sample(second, rows[heldout] + dy / resolution, cols[heldout] - dx / resolution)
    held_after = targets[heldout] - sampled - bias
    before = _metrics(held_before)
    after = _metrics(held_after)
    if after["rmse_m"] > before["rmse_m"] + max(1e-6, before["rmse_m"] * .01):
        raise ValueError("Heldout agreement worsens after registration")
    aligned = shift_array(second, dx, dy, resolution) + bias
    return {
        "shift_east_m": dx, "shift_north_m": dy,
        "vertical_offset_removed_m": bias,
        "aligned_reference": aligned,
        "converged": True, "iterations": iteration,
        "resolution_m": resolution, "max_shift_m_per_axis": bound,
        "fit_cells": int(train.size), "heldout_cells": int(heldout.size),
        "before_heldout": before, "after_heldout": after,
        "training_residual": _metrics(training),
        "zero_shift_training_vertical_bias_m": bias0,
        "method": "bounded fixed-Huber gradient/pattern translation with bilinear sampling and median vertical offset",
        "interpretation": "internal stable-terrain agreement, not absolute geodetic accuracy or independent uncertainty",
        "reference": "https://doi.org/10.5194/tc-5-271-2011",
    }
