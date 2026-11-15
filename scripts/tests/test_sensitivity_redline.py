"""Tornado assembly: bars sorted by swing, signed against the base, inputs never silently dropped."""
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sensitivity_redline", ROOT / "scripts/sensitivity_redline.py")
sens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sens)


def test_bars_are_sorted_by_total_swing_and_keep_signs():
    rows = [{"parameter": "z", "low": 1.28, "high": 2.33, "metric_low": 0.45, "metric_high": 0.30},
            {"parameter": "sep", "low": 15, "high": 30, "metric_low": 0.25, "metric_high": 0.80}]
    bars = sens.tornado(0.38, rows)
    assert [b["parameter"] for b in bars] == ["sep", "z"]
    assert bars[0]["delta_low"] == pytest.approx(-0.13)
    assert bars[0]["delta_high"] == pytest.approx(0.42)
    assert bars[0]["swing"] == pytest.approx(0.55)
    assert bars[1]["delta_low"] == pytest.approx(0.07)


def test_non_finite_metric_is_rejected():
    with pytest.raises(ValueError, match="z"):
        sens.tornado(0.38, [{"parameter": "z", "low": 1, "high": 2, "metric_low": math.nan, "metric_high": 0.3}])
