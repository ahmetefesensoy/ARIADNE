"""Display geometry: small-hole filling and Douglas-Peucker ring simplification."""
import numpy as np
import pytest
from skimage.measure import approximate_polygon

from redline_core.polyline import fill_small_holes, simplify_ring
from redline_core.redline import region_contours


def test_fill_small_holes_fills_only_small_enclosed_pockets():
    work = np.ones((8, 8))
    work[2, 2] = -1.0                 # 1-cell enclosed pocket
    work[4:7, 4:7] = -1.0             # 9-cell enclosed pocket
    work[0, 6:8] = -1.0               # touches the border: never filled
    out = fill_small_holes(work, 0.0, 4, 5.0)
    assert out[2, 2] == 5.0
    assert (out[4:7, 4:7] == -1.0).all() and (out[0, 6:8] == -1.0).all()
    assert work[2, 2] == -1.0  # input untouched
    np.testing.assert_array_equal(fill_small_holes(work, 0.0, 0, 5.0), work)


def test_fill_uses_4_connectivity_for_pockets():
    work = np.ones((6, 6))
    work[1, 1] = work[2, 2] = -1.0  # diagonal neighbours: two separate 1-cell pockets
    out = fill_small_holes(work, 0.0, 2, 9.0)
    assert out[1, 1] == 9.0 and out[2, 2] == 9.0


def test_region_contours_drops_small_holes_but_keeps_the_outer_ring():
    margin = np.full((12, 12), 100.0)
    margin[5, 5] = np.nan
    margin[0, :] = -10.0
    all_rings = region_contours(margin, (0.0, 0.0), 4.0, 0.0)
    filtered = region_contours(margin, (0.0, 0.0), 4.0, 0.0, min_hole_cells=2)
    assert len(all_rings) == 2 and len(filtered) == 1
    np.testing.assert_allclose(filtered[0], all_rings[int(np.argmax([len(r) for r in all_rings]))])


@pytest.mark.parametrize("tolerance", [0.5, 2.0, 8.0])
def test_simplify_matches_skimage_douglas_peucker(tolerance):
    t = np.linspace(0, 2 * np.pi, 400)
    radius = 50 + 6 * np.sin(7 * t) + np.random.default_rng(2).normal(0, 0.3, t.size)
    ring = np.column_stack([radius * np.cos(t), radius * np.sin(t)])
    ring[-1] = ring[0]
    ours = simplify_ring(ring, tolerance)
    reference = approximate_polygon(ring, tolerance)
    np.testing.assert_allclose(ours, reference)
    assert np.array_equal(ours[0], ours[-1])


def test_simplify_keeps_extra_columns_and_handles_trivial_input():
    ring = np.array([[0, 0, 1], [1, 0.01, 2], [2, 0, 3], [2, 2, 4], [0, 0, 1]], dtype=float)
    out = simplify_ring(ring, 0.1)
    assert out.shape[1] == 3 and [1, 0.01, 2] not in out.tolist()
    np.testing.assert_array_equal(simplify_ring(ring, 0.0), ring)
    np.testing.assert_array_equal(simplify_ring(ring[:2], 1.0), ring[:2])
