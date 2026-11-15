"""Bayesian science value: posterior, exact joint EIG, diminishing returns (§7.10)."""
import itertools
import math
from pathlib import Path

import numpy as np
import pytest

from redline_core.science_value import ScienceModel, entropy_bits, joint_eig_bits, load_science, posterior

REPO = Path(__file__).resolve().parents[3]
MODEL = ScienceModel("TST", "q", ("H1", "H2", "H3"), np.array([1 / 3] * 3),
                     {"ridge": np.array([0.85, 0.15, 0.5]), "hollow": np.array([0.85, 0.15, 0.5])})


def brute_eig(model, prior, classes):
    """Mutual information I(H; O) from the full joint table (independent of the module)."""
    total = 0.0
    for outcome in itertools.product((1, 0), repeat=len(classes)):
        for h in range(len(prior)):
            p_o_given_h = 1.0
            for cls, o in zip(classes, outcome):
                p = model.p_seen[cls][h]
                p_o_given_h *= p if o else 1 - p
            p_o = sum(prior[k] * np.prod([(model.p_seen[c][k] if o else 1 - model.p_seen[c][k])
                                          for c, o in zip(classes, outcome)]) for k in range(len(prior)))
            joint = prior[h] * p_o_given_h
            if joint > 0:
                total += joint * math.log2(p_o_given_h / p_o)
    return total


def test_joint_eig_equals_mutual_information():
    for classes in (["ridge"], ["ridge", "hollow"], ["ridge", "ridge", "hollow"]):
        assert joint_eig_bits(MODEL, MODEL.prior, classes) == pytest.approx(brute_eig(MODEL, MODEL.prior, classes))


def test_eig_is_bounded_by_prior_entropy_and_shows_diminishing_returns():
    one = joint_eig_bits(MODEL, MODEL.prior, ["ridge"])
    two = joint_eig_bits(MODEL, MODEL.prior, ["ridge", "ridge"])
    assert 0 < one < two < 2 * one
    many = joint_eig_bits(MODEL, MODEL.prior, ["ridge", "hollow"] * 6)
    assert many < entropy_bits(MODEL.prior) == pytest.approx(math.log2(3))
    assert joint_eig_bits(MODEL, MODEL.prior, []) == 0.0


def test_posterior_moves_toward_the_supported_hypothesis():
    post = posterior(MODEL, MODEL.prior, ["ridge", "hollow"], [True, True])
    assert post.argmax() == 0 and post.sum() == pytest.approx(1.0)
    assert posterior(MODEL, MODEL.prior, ["ridge"], [False]).argmax() == 1
    # A certain prior learns nothing.
    certain = np.array([1.0 - 2e-12, 1e-12, 1e-12])
    assert joint_eig_bits(MODEL, certain, ["ridge"]) == pytest.approx(0.0, abs=1e-9)


def test_rejects_bad_models_and_unknown_classes():
    with pytest.raises(ValueError):
        ScienceModel("T", "", ("A", "B"), np.array([0.6, 0.6]), {})
    with pytest.raises(ValueError):
        ScienceModel("T", "", ("A", "B"), np.array([0.5, 0.5]), {"x": np.array([1.0, 0.2])})
    with pytest.raises(ValueError):
        joint_eig_bits(MODEL, MODEL.prior, ["crater"])
    with pytest.raises(ValueError):
        joint_eig_bits(MODEL, MODEL.prior, ["ridge"] * 15)


def test_repo_bxw_science_config_loads():
    model = load_science(REPO / "config" / "science_BXW.yaml")
    assert model.site_id == "BXW" and len(model.hypotheses) == 3
    assert set(model.p_seen) == {"ridge", "hollow"}
