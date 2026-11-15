"""Terrain-derived science targets: TPI sign, spacing, eligibility (D011)."""
import numpy as np
import pytest

from redline_core.targets import pick_targets, topographic_position_index


def test_tpi_is_positive_on_a_ridge_and_negative_in_a_hollow():
    y, x = np.mgrid[0:80, 0:80].astype(float)
    z = 2.0 * np.exp(-((x - 20) ** 2) / 8.0) - 2.0 * np.exp(-((x - 60) ** 2) / 8.0)
    tpi = topographic_position_index(z, 1.0, 3.0, 10.0)
    assert tpi[40, 20] > 1.0 and tpi[40, 60] < -1.0 and abs(tpi[40, 40]) < 0.1
    with pytest.raises(ValueError):
        topographic_position_index(z, 1.0, 5.0, 5.0)


def test_pick_targets_respects_class_spacing_and_eligibility():
    tpi = np.zeros((30, 30))
    tpi[5, 5], tpi[5, 6], tpi[20, 20] = 3.0, 2.9, 2.0   # two ridge peaks close together, one far
    tpi[10, 25], tpi[25, 3] = -2.5, -1.5
    eligible = np.ones_like(tpi, dtype=bool)
    eligible[25, 3] = False
    targets = pick_targets(tpi, eligible, 4.0, per_class=3, min_spacing_m=20.0, min_abs_tpi_m=1.0)
    cells = {t.cell: t.science_class for t in targets}
    assert cells == {(5, 5): "ridge", (20, 20): "ridge", (10, 25): "hollow"}
    assert [t.target_id for t in targets] == ["T01", "T02", "T03"]
