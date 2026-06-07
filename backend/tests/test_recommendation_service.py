from app.recommendations.service import build_recommendation


def test_builds_active_watch_recommendation_with_explanation_and_risk_fields():
    recommendation = build_recommendation(
        ticker="PAX",
        features={
            "gap_percent": 7.5,
            "relative_volume": 3.2,
            "liquidity_score": 92,
            "price": 11.5,
            "spread_percent": 0.08,
            "vwap": 11.2,
            "current_price": 11.55,
            "atr_percent": 4.0,
        },
        catalyst={"catalyst_type": "insider_director_purchase", "signal": "bullish", "score": 90, "strength": "strong"},
        market_context={"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up", "iwm_trend": "neutral"},
    )

    assert recommendation["ticker"] == "PAX"
    assert recommendation["timeframe"] == "day_trade"
    assert recommendation["status"] == "active_watch"
    assert recommendation["strategy"] == "catalyst_momentum_gap_and_go"
    assert recommendation["direction"] == "long"
    assert recommendation["setup_score"] == 93
    assert recommendation["confidence"] == "high"
    assert recommendation["entry_zone"] == [11.43, 11.67]
    assert recommendation["stop_loss"] == 11.09
    assert recommendation["targets"] == [12.24, 12.75]
    assert recommendation["risk_reward"] == 1.5
    assert "Strong bullish catalyst" in recommendation["reason"]
    assert "relative volume 3.2x" in recommendation["reason"]
    assert recommendation["invalid_if"] == ["loses VWAP", "relative volume fades", "market context turns risk_off"]


def test_builds_no_trade_recommendation_with_rejection_reasons():
    recommendation = build_recommendation(
        ticker="THIN",
        features={
            "gap_percent": 9,
            "relative_volume": 4,
            "liquidity_score": 25,
            "price": 8,
            "spread_percent": 3.0,
            "current_price": 8.2,
            "atr_percent": 8.0,
        },
        catalyst={"catalyst_type": "insider_director_purchase", "signal": "bullish", "score": 90, "strength": "strong"},
        market_context={"risk_context": "supportive"},
    )

    assert recommendation["status"] == "no_trade"
    assert recommendation["entry_zone"] is None
    assert recommendation["stop_loss"] is None
    assert recommendation["targets"] == []
    assert "liquidity_score_below_min" in recommendation["reject_reasons"]
    assert "spread_too_wide" in recommendation["reject_reasons"]
    assert "No trade" in recommendation["reason"]


def test_caution_recommendation_preserves_risk_off_warning():
    recommendation = build_recommendation(
        ticker="AAPL",
        features={"gap_percent": 7, "relative_volume": 3, "liquidity_score": 90, "price": 210, "spread_percent": 0.04, "current_price": 211},
        catalyst={"catalyst_type": "earnings_beat", "signal": "bullish", "score": 90, "strength": "strong"},
        market_context={"risk_context": "risk_off", "spy_trend": "down", "qqq_trend": "down"},
    )

    assert recommendation["status"] == "caution"
    assert recommendation["warnings"] == ["market_context_risk_off"]
    assert "risk-off market context" in recommendation["reason"]


def test_recommendation_uses_custom_actionable_threshold_for_research_runs():
    features = {
        "gap_percent": 1.0,
        "relative_volume": 1.5,
        "liquidity_score": 90,
        "price": 210,
        "spread_percent": 0.03,
        "current_price": 212,
        "vwap": 211,
    }
    catalyst = {"catalyst_type": "unknown", "signal": "neutral", "score": 0, "strength": "weak"}
    market_context = {"risk_context": "supportive"}

    recommendation = build_recommendation(
        "AAPL",
        features,
        catalyst,
        market_context,
        actionable_score_threshold=35,
    )

    assert recommendation["setup_score"] == 38
    assert recommendation["status"] == "active_watch"
    assert recommendation["entry_zone"] == [209.88, 214.12]


def test_recommendation_exposes_research_segment_metadata():
    recommendation = build_recommendation(
        ticker="AAPL",
        features={
            "gap_percent": 1,
            "relative_volume": 3,
            "liquidity_score": 95,
            "price": 210,
            "spread_percent": 0.03,
            "current_price": 212,
            "vwap": 211,
        },
        catalyst={"catalyst_type": "contract_win", "signal": "bullish", "score": 65, "strength": "medium"},
        market_context={"risk_context": "neutral"},
    )

    assert recommendation["strategy_segment"] == "vwap_hold_reclaim|contract_win"
    assert recommendation["research_tags"] == ["segment_edge_candidate"]
    assert recommendation["research_evidence"] is None
    assert "research-supported segment" in recommendation["reason"]


def test_recommendation_exposes_research_evidence_for_context_supported_segment():
    recommendation = build_recommendation(
        ticker="AAPL",
        features={
            "gap_percent": 1,
            "relative_volume": 3,
            "liquidity_score": 95,
            "price": 210,
            "spread_percent": 0.03,
            "current_price": 212,
            "vwap": 211,
        },
        catalyst={"signal": "bullish", "score": 65, "catalyst_type": "contract_win"},
        market_context={"risk_context": "supportive"},
    )

    assert "market_context_edge_candidate" in recommendation["research_tags"]
    assert recommendation["research_evidence"] == {
        "market_context_segment": "vwap_hold_reclaim|contract_win|supportive",
        "recommended_threshold": 60,
        "trade_count": 74,
        "win_rate": 0.45,
        "expectancy_r": 0.11,
    }


def test_recommendation_contains_structured_input_snapshots_for_learning():
    features = {"gap_percent": 1.2, "relative_volume": 2.5, "liquidity_score": 100, "price": 210, "spread_percent": 0.03, "current_price": 212, "opening_range_high": 211.5, "vwap": 211}
    catalyst = {"catalyst_type": "unknown", "signal": "neutral", "score": 0, "strength": "weak"}
    market_context = {"risk_context": "supportive"}

    recommendation = build_recommendation("AAPL", features, catalyst, market_context)

    assert recommendation["inputs"] == {
        "features": features,
        "catalyst": catalyst,
        "market_context": market_context,
    }
    assert recommendation["strategy"] == "opening_range_breakout"
