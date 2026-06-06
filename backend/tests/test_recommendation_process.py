from app.catalysts.classifier import classify_catalyst
from app.features.liquidity import calculate_liquidity_score, calculate_relative_volume, calculate_spread_percent
from app.features.market_context import summarize_market_context
from app.features.technicals import calculate_atr_percent, calculate_gap_percent, calculate_vwap
from app.recommendations.service import build_recommendation


def test_recommendation_process_from_raw_inputs_to_active_watch():
    intraday_candles = [
        {"high": 11.7, "low": 11.1, "close": 11.55, "volume": 500_000},
        {"high": 11.9, "low": 11.4, "close": 11.8, "volume": 700_000},
    ]
    daily_candles = [
        {"high": 10.5, "low": 9.9, "close": 10.2},
        {"high": 11.9, "low": 10.8, "close": 11.8},
    ]
    raw_catalyst = {"catalyst_type": "insider_director_purchase"}

    features = {
        "gap_percent": calculate_gap_percent(previous_close=10.2, current_price=11.55),
        "relative_volume": calculate_relative_volume(current_volume=3_200_000, average_volume=1_000_000),
        "liquidity_score": calculate_liquidity_score(price=11.55, volume=3_200_000, average_volume=1_000_000, bid=11.54, ask=11.56),
        "spread_percent": calculate_spread_percent(bid=11.54, ask=11.56),
        "vwap": calculate_vwap(intraday_candles),
        "current_price": 11.55,
        "price": 11.55,
        "atr_percent": calculate_atr_percent(daily_candles, period=2),
    }
    catalyst = classify_catalyst(raw_catalyst)
    market_context = summarize_market_context(
        {
            "SPY": [{"close": 100}, {"close": 101}, {"close": 102}, {"close": 103}, {"close": 104}],
            "QQQ": [{"close": 200}, {"close": 202}, {"close": 204}, {"close": 206}, {"close": 208}],
            "IWM": [{"close": 190}, {"close": 190}, {"close": 190}, {"close": 190}, {"close": 190}],
        }
    )

    recommendation = build_recommendation("PAX", features, catalyst, market_context)

    assert recommendation["status"] == "active_watch"
    assert recommendation["strategy"] == "catalyst_momentum_gap_and_go"
    assert recommendation["setup_score"] >= 85
    assert recommendation["inputs"]["features"]["gap_percent"] == 13.24
    assert recommendation["inputs"]["catalyst"]["score"] == 90


def test_recommendation_process_rejects_bad_liquidity_before_actionability():
    features = {
        "gap_percent": 30,
        "relative_volume": 6,
        "liquidity_score": calculate_liquidity_score(price=4.2, volume=80_000, average_volume=100_000, bid=4.0, ask=4.4),
        "spread_percent": calculate_spread_percent(bid=4.0, ask=4.4),
        "current_price": 4.2,
        "price": 4.2,
    }

    recommendation = build_recommendation(
        "BAD",
        features,
        classify_catalyst({"catalyst_type": "insider_cluster_buying"}),
        {"risk_context": "supportive"},
    )

    assert recommendation["status"] == "no_trade"
    assert recommendation["entry_zone"] is None
    assert "price_below_min" in recommendation["reject_reasons"]
    assert "liquidity_score_below_min" in recommendation["reject_reasons"]
    assert "spread_too_wide" in recommendation["reject_reasons"]
