from app.strategies.day_trading import score_day_trade_setup


def test_scores_catalyst_momentum_gap_and_go_as_active_watch():
    result = score_day_trade_setup(
        ticker="PAX",
        features={
            "gap_percent": 7.5,
            "relative_volume": 3.2,
            "liquidity_score": 92,
            "price": 11.5,
            "spread_percent": 0.08,
            "vwap": 11.2,
            "current_price": 11.55,
        },
        catalyst={"signal": "bullish", "score": 90, "catalyst_type": "insider_director_purchase"},
        market_context={"risk_context": "supportive"},
    )

    assert result["ticker"] == "PAX"
    assert result["strategy"] == "catalyst_momentum_gap_and_go"
    assert result["direction"] == "long"
    assert result["setup_score"] == 93
    assert result["confidence"] == "high"
    assert result["status"] == "active_watch"
    assert result["entry_trigger"] == "break_above_intraday_high_or_clean_vwap_hold"
    assert result["invalid_if"] == ["loses VWAP", "relative volume fades", "market context turns risk_off"]


def test_returns_no_trade_for_weak_liquidity_even_with_catalyst():
    result = score_day_trade_setup(
        ticker="THIN",
        features={
            "gap_percent": 9,
            "relative_volume": 4,
            "liquidity_score": 25,
            "price": 8,
            "spread_percent": 3.0,
            "vwap": 8.1,
            "current_price": 8.2,
        },
        catalyst={"signal": "bullish", "score": 90, "catalyst_type": "insider_director_purchase"},
        market_context={"risk_context": "supportive"},
    )

    assert result["status"] == "no_trade"
    assert "liquidity_score_below_min" in result["reject_reasons"]
    assert "spread_too_wide" in result["reject_reasons"]


def test_returns_no_trade_for_penny_stock_filter():
    result = score_day_trade_setup(
        ticker="CHEAP",
        features={"gap_percent": 20, "relative_volume": 10, "liquidity_score": 95, "price": 4.5, "spread_percent": 0.1},
        catalyst={"signal": "bullish", "score": 95, "catalyst_type": "insider_cluster_buying"},
        market_context={"risk_context": "supportive"},
    )

    assert result["status"] == "no_trade"
    assert "price_below_min" in result["reject_reasons"]


def test_opening_range_breakout_scores_without_catalyst_when_volume_and_market_support():
    result = score_day_trade_setup(
        ticker="AAPL",
        features={
            "gap_percent": 1.2,
            "relative_volume": 2.5,
            "liquidity_score": 100,
            "price": 210,
            "spread_percent": 0.03,
            "current_price": 212,
            "opening_range_high": 211.5,
            "vwap": 211,
        },
        catalyst={"signal": "neutral", "score": 0, "catalyst_type": "unknown"},
        market_context={"risk_context": "supportive"},
    )

    assert result["strategy"] == "opening_range_breakout"
    assert result["status"] == "active_watch"
    assert result["setup_score"] == 76


def test_custom_actionable_threshold_can_promote_research_setups_without_changing_defaults():
    features = {
        "gap_percent": 1.0,
        "relative_volume": 1.5,
        "liquidity_score": 90,
        "price": 210,
        "spread_percent": 0.03,
        "current_price": 212,
        "vwap": 211,
    }
    catalyst = {"signal": "neutral", "score": 0, "catalyst_type": "unknown"}
    market_context = {"risk_context": "supportive"}

    default_result = score_day_trade_setup("AAPL", features, catalyst, market_context)
    research_result = score_day_trade_setup(
        "AAPL",
        features,
        catalyst,
        market_context,
        actionable_score_threshold=35,
    )

    assert default_result["setup_score"] == 38
    assert default_result["status"] == "no_trade"
    assert research_result["setup_score"] == 38
    assert research_result["status"] == "active_watch"


def test_risk_off_market_context_caps_status_to_caution():
    result = score_day_trade_setup(
        ticker="AAPL",
        features={"gap_percent": 7, "relative_volume": 3, "liquidity_score": 90, "price": 210, "spread_percent": 0.04},
        catalyst={"signal": "bullish", "score": 90, "catalyst_type": "earnings_beat"},
        market_context={"risk_context": "risk_off"},
    )

    assert result["status"] == "caution"
    assert "market_context_risk_off" in result["warnings"]
