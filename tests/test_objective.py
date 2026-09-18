"""Margin objective, simplex repair, constraints."""

import numpy as np
import pytest

from dangote_opt.optimization.objective import RefineryObjective, simplex_repair


@pytest.fixture
def obj():
    return RefineryObjective(
        crude_apis=np.array([35.0] * 5),
        crude_sulfurs=np.array([0.4] * 5),
        crude_costs=np.array([80.0, 82.0, 78.0, 85.0, 81.0]),
        product_prices=np.array([95.0, 100.0, 90.0, 70.0]),
    )


def test_simplex_repair_normalizes():
    x = simplex_repair(np.array([2.0, 1.0, 1.0, 0.0, 0.0]))
    assert x.sum() == pytest.approx(1.0)
    assert (x >= 0).all()


def test_simplex_repair_zero_vector_gives_uniform():
    assert np.allclose(simplex_repair(np.zeros(5)), np.full(5, 0.2))


def test_equal_weight_is_feasible(obj):
    assert obj.constraints_violated(np.full(5, 0.2), 0.5) == []


def test_sour_blend_violates_sulfur_cap():
    sour = RefineryObjective(
        crude_apis=np.array([31.0] * 5),
        crude_sulfurs=np.array([2.0] * 5),
        crude_costs=np.array([70.0] * 5),
        product_prices=np.array([95.0, 100.0, 90.0, 70.0]),
    )
    violations = sour.constraints_violated(np.full(5, 0.2), 0.5)
    assert any("S_blend" in v for v in violations)


def test_objective_is_negative_margin(obj):
    x = np.zeros(6)
    x[:5] = 0.2
    expected = -(0.30 * 95 + 0.30 * 100 + 0.15 * 90 + 0.10 * 70 - 0.2 * (80 + 82 + 78 + 85 + 81))
    assert obj(x) == pytest.approx(expected)


def test_placeholder_yields_stay_bounded(obj):
    y = obj.predict_yields(np.full(5, 0.2), 1.0)
    assert (y >= 0).all() and (y <= 1).all()


def test_wrong_lengths_raise():
    with pytest.raises(ValueError, match="length 5"):
        RefineryObjective(
            crude_apis=np.array([35.0] * 3),
            crude_sulfurs=np.array([0.4] * 5),
            crude_costs=np.array([80.0] * 5),
            product_prices=np.array([95.0, 100.0, 90.0, 70.0]),
        )
