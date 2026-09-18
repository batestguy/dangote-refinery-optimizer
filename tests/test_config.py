"""Config invariants — the locked scope guards live in code, not just prose."""

from dangote_opt.config import CONFIG


def test_products_locked_to_four():
    assert len(CONFIG.products) == 4


def test_prices_match_products():
    assert set(CONFIG.default_prices) == set(CONFIG.products)


def test_scope_guards():
    assert CONFIG.n_crudes == 5
    assert CONFIG.severity_bounds == (0.0, 1.0)


def test_de_budget_respects_app_latency_target():
    # spec §3.7: deep re-opt must land in the 30–60 s window on free tier
    assert CONFIG.de_maxiter <= 300
    assert CONFIG.de_popsize <= 20
