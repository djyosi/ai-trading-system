from app.strategies.day_trading import score_day_trade_setup


_features = {
    "gap_percent": 7.5,
    "relative_volume": 3.2,
    "liquidity_score": 92,
    "price": 11.5,
    "spread_percent": 0.08,
    "vwap": 11.2,
    "current_price": 11.55,
}
_catalyst = {"signal": "bullish", "score": 90, "catalyst_type": "insider_director_purchase"}
_market = {"risk_context": "supportive"}


def test_bullish_chart_pattern_boosts_score():
    features = {**_features, "chart_pattern": {"pattern": "hammer", "direction": "bullish", "strength": "moderate"}}

    result = score_day_trade_setup("PAX", features, _catalyst, _market)

    assert result["setup_score"] == 98  # 93 + 5


def test_bearish_chart_pattern_reduces_score():
    features = {**_features, "chart_pattern": {"pattern": "shooting_star", "direction": "bearish", "strength": "moderate"}}

    result = score_day_trade_setup("PAX", features, _catalyst, _market)

    assert result["setup_score"] == 88  # 93 - 5


def test_no_chart_pattern_no_effect():
    result = score_day_trade_setup("PAX", _features, _catalyst, _market)

    assert result["setup_score"] == 93  # unchanged, no pattern
