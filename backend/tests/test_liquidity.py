from app.features.liquidity import (
    calculate_dollar_volume,
    calculate_liquidity_score,
    calculate_relative_volume,
    calculate_spread_percent,
)


def test_calculate_dollar_volume():
    assert calculate_dollar_volume(price=25.50, volume=1_000_000) == 25_500_000


def test_calculate_dollar_volume_returns_none_for_missing_inputs():
    assert calculate_dollar_volume(price=None, volume=1_000_000) is None
    assert calculate_dollar_volume(price=25.50, volume=None) is None


def test_calculate_spread_percent_from_bid_ask_midpoint():
    assert calculate_spread_percent(bid=99.95, ask=100.05) == 0.1


def test_calculate_spread_percent_returns_none_for_bad_quote():
    assert calculate_spread_percent(bid=0, ask=100) is None
    assert calculate_spread_percent(bid=101, ask=100) is None


def test_calculate_relative_volume():
    assert calculate_relative_volume(current_volume=3_000_000, average_volume=1_000_000) == 3.0


def test_calculate_relative_volume_returns_none_for_zero_average():
    assert calculate_relative_volume(current_volume=3_000_000, average_volume=0) is None


def test_liquidity_score_rewards_liquid_tight_spread_names():
    score = calculate_liquidity_score(
        price=50,
        volume=2_000_000,
        average_volume=1_000_000,
        bid=49.99,
        ask=50.01,
    )

    assert score == 100


def test_liquidity_score_penalizes_thin_wide_spread_names():
    score = calculate_liquidity_score(
        price=6,
        volume=100_000,
        average_volume=750_000,
        bid=5.90,
        ask=6.10,
    )

    assert score == 25
