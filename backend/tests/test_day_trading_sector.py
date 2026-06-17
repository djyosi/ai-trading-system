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


def test_sector_in_output_for_known_ticker():
    result = score_day_trade_setup("AAPL", _features, _catalyst, _market)

    assert result["sector"] == "technology"


def test_sector_in_output_for_utility():
    result = score_day_trade_setup("DUK", _features, _catalyst, _market)

    assert result["sector"] == "utilities"


def test_sector_in_output_for_unknown_ticker():
    result = score_day_trade_setup("XYZ", _features, _catalyst, _market)

    assert result["sector"] == "unknown"
