"""Linear blending rules."""

import numpy as np
import pytest

from dangote_opt.features.blend import blend_api, blend_property, blend_sulfur


def test_weighted_average():
    assert blend_property([0.5, 0.5], [30.0, 40.0]) == pytest.approx(35.0)


def test_single_crude_dominates():
    assert blend_api([1.0, 0.0], [33.4, 20.0]) == pytest.approx(33.4)


def test_sulfur_linear():
    assert blend_sulfur([0.75, 0.25], [0.2, 1.0]) == pytest.approx(0.4)


def test_shape_mismatch_raises():
    with pytest.raises(ValueError, match="shape mismatch"):
        blend_property([1.0, 0.0], [1.0])


def test_negative_ratio_raises():
    with pytest.raises(ValueError, match="non-negative"):
        blend_property([-0.5, 1.5], [30.0, 40.0])


def test_vectorized_input():
    ratios = np.array([[0.5, 0.5], [1.0, 0.0]])
    values = np.array([30.0, 50.0])
    out = np.array([blend_property(r, values) for r in ratios])
    assert out[0] == pytest.approx(40.0)
