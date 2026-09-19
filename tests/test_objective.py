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


def test_objective_is_negative_margin_when_feasible(obj):
    # Hand-computed: API 35 -> light = (35-30)/15 = 1/3; S = 0.4; severity 0.
    light = 1 / 3
    yields = np.array(
        [
            0.25 + 0.10 * light,  # gasoline
            0.30 + 0.02 * light - 0.02 * 0.4,  # diesel
            0.15 + 0.02 * light,  # jet
            0.12 - 0.04 * light,  # petrochem
        ]
    )
    revenue = float(yields @ np.array([95.0, 100.0, 90.0, 70.0]))
    cost = 0.2 * (80 + 82 + 78 + 85 + 81)
    ratios = np.full(5, 0.2)
    assert obj.violation_magnitude(ratios) == 0.0
    assert obj.margin(ratios, 0.0) == pytest.approx(revenue - cost)
    assert obj(np.r_[ratios, 0.0]) == pytest.approx(-(revenue - cost))


def test_placeholder_yields_stay_bounded(obj):
    for sev in (0.0, 0.5, 1.0):
        y = obj.predict_yields(np.full(5, 0.2), sev)
        assert (y >= 0).all() and (y <= 1).all()
        assert y.sum() < 1.0  # remainder is fuel oil / loss


def test_lighter_blend_yields_more_gasoline():
    prices = np.array([95.0, 100.0, 90.0, 70.0])
    sulfurs, costs = np.array([0.3] * 5), np.array([80.0] * 5)
    heavy = RefineryObjective(np.array([31.0] * 5), sulfurs, costs, prices)
    light = RefineryObjective(np.array([40.0] * 5), sulfurs, costs, prices)
    x = np.full(5, 0.2)
    assert light.predict_yields(x, 0.5)[0] > heavy.predict_yields(x, 0.5)[0]
    assert light.predict_yields(x, 0.5)[3] < heavy.predict_yields(x, 0.5)[3]


def test_severity_shifts_to_gasoline(obj):
    x = np.full(5, 0.2)
    low, high = obj.predict_yields(x, 0.0), obj.predict_yields(x, 1.0)
    assert high[0] > low[0]
    assert high[1] < low[1]


def test_infeasible_blend_is_penalized():
    prices = np.array([95.0, 100.0, 90.0, 70.0])
    # crude 0: sweet but expensive; crude 1: very sour but nearly free
    obj = RefineryObjective(
        crude_apis=np.array([34.0, 34.0, 34.0, 34.0, 34.0]),
        crude_sulfurs=np.array([0.2, 3.0, 0.2, 0.2, 0.2]),
        crude_costs=np.array([80.0, 1.0, 80.0, 80.0, 80.0]),
        product_prices=prices,
    )
    feasible = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.5])
    infeasible = np.array([0.0, 1.0, 0.0, 0.0, 0.0, 0.5])  # S_blend = 3.0 > 1.5 cap
    assert obj.violation_magnitude(infeasible[:5]) > 0
    # Without the penalty the near-free sour barrel would win; with it, it must not.
    assert obj(infeasible) > obj(feasible)


def test_tiny_violation_still_uneconomic():
    # 0.01 wt-% over the sulfur cap must cost more than the margin gain from a
    # realistically discounted sour barrel (~$10/bbl cheaper, cf. Urals vs Bonny
    # in the app slate) — that's what the linear penalty term guarantees.
    prices = np.array([95.0, 100.0, 90.0, 70.0])
    obj = RefineryObjective(
        crude_apis=np.array([34.0] * 5),
        crude_sulfurs=np.array([0.2, 1.51, 0.2, 0.2, 0.2]),
        crude_costs=np.array([78.0, 68.0, 78.0, 78.0, 78.0]),
        product_prices=prices,
    )
    feasible = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.5])
    barely_infeasible = np.array([0.0, 1.0, 0.0, 0.0, 0.0, 0.5])
    assert obj.violation_magnitude(barely_infeasible[:5]) == pytest.approx(0.01 + 0.01**2)
    assert obj(barely_infeasible) > obj(feasible)


def test_api_window_violation_measured_symmetrically(obj):
    lo, hi = obj.config.api_blend_range
    too_heavy = RefineryObjective(
        crude_apis=np.array([lo - 2.0] * 5),
        crude_sulfurs=obj.crude_sulfurs,
        crude_costs=obj.crude_costs,
        product_prices=obj.product_prices,
    )
    too_light = RefineryObjective(
        crude_apis=np.array([hi + 2.0] * 5),
        crude_sulfurs=obj.crude_sulfurs,
        crude_costs=obj.crude_costs,
        product_prices=obj.product_prices,
    )
    x = np.full(5, 0.2)
    assert too_heavy.violation_magnitude(x) == pytest.approx(2.0 + 4.0)  # v + v², v = 2
    assert too_light.violation_magnitude(x) == pytest.approx(2.0 + 4.0)


def test_wrong_lengths_raise():
    with pytest.raises(ValueError, match="length 5"):
        RefineryObjective(
            crude_apis=np.array([35.0] * 3),
            crude_sulfurs=np.array([0.4] * 5),
            crude_costs=np.array([80.0] * 5),
            product_prices=np.array([95.0, 100.0, 90.0, 70.0]),
        )
