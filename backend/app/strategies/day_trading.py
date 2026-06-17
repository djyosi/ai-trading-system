MIN_PRICE = 5
MIN_LIQUIDITY_SCORE = 60
MAX_SPREAD_PERCENT = 0.75
RESEARCH_SUPPORTED_SEGMENTS = {
    ("vwap_hold_reclaim", "contract_win"),
    ("catalyst_momentum_gap_and_go", "analyst_upgrade"),
}
RESEARCH_SUPPORTED_MARKET_CONTEXT_SEGMENTS = {
    ("vwap_hold_reclaim", "contract_win", "mixed"): {
        "market_context_segment": "vwap_hold_reclaim|contract_win|mixed",
        "recommended_threshold": 60,
        "trade_count": 25,
        "win_rate": 0.52,
        "expectancy_r": 0.30,
    },
    ("vwap_hold_reclaim", "contract_win", "supportive"): {
        "market_context_segment": "vwap_hold_reclaim|contract_win|supportive",
        "recommended_threshold": 60,
        "trade_count": 74,
        "win_rate": 0.45,
        "expectancy_r": 0.11,
    },
    ("catalyst_momentum_gap_and_go", "analyst_upgrade", "supportive"): {
        "market_context_segment": "catalyst_momentum_gap_and_go|analyst_upgrade|supportive",
        "recommended_threshold": 60,
        "trade_count": 38,
        "win_rate": 0.45,
        "expectancy_r": 0.12,
    },
}


def score_day_trade_setup(ticker, features, catalyst, market_context, actionable_score_threshold=70):
    reject_reasons = _reject_reasons(features)
    warnings = []
    if market_context.get("risk_context") == "risk_off":
        warnings.append("market_context_risk_off")

    strategy = _select_strategy(features, catalyst)
    strategy_segment = _strategy_segment(strategy, catalyst)
    research_tags = _apply_segment_policy(strategy, catalyst, market_context, reject_reasons, warnings)
    research_evidence = _research_evidence(strategy, catalyst, market_context)
    setup_score = _calculate_score(features, catalyst, market_context, strategy)
    status = _status(setup_score, reject_reasons, warnings, actionable_score_threshold)

    return {
        "ticker": ticker,
        "strategy": strategy,
        "strategy_segment": strategy_segment,
        "research_tags": research_tags,
        "research_evidence": research_evidence,
        "direction": "long" if catalyst.get("signal") != "bearish" else "short_watch",
        "setup_score": setup_score,
        "confidence": _confidence(setup_score),
        "status": status,
        "entry_trigger": _entry_trigger(strategy),
        "invalid_if": ["loses VWAP", "relative volume fades", "market context turns risk_off"],
        "reject_reasons": reject_reasons,
        "warnings": warnings,
    }


def _reject_reasons(features):
    reasons = []
    if (features.get("price") or 0) < MIN_PRICE:
        reasons.append("price_below_min")
    if (features.get("liquidity_score") or 0) < MIN_LIQUIDITY_SCORE:
        reasons.append("liquidity_score_below_min")
    spread_percent = features.get("spread_percent")
    if spread_percent is not None and spread_percent > MAX_SPREAD_PERCENT:
        reasons.append("spread_too_wide")
    return reasons


def _select_strategy(features, catalyst):
    current_price = features.get("current_price")
    opening_range_high = features.get("opening_range_high")
    if catalyst.get("signal") == "bullish" and catalyst.get("score", 0) >= 60 and (features.get("gap_percent") or 0) >= 5:
        return "catalyst_momentum_gap_and_go"
    if current_price is not None and opening_range_high is not None and current_price > opening_range_high:
        return "opening_range_breakout"
    if current_price is not None and features.get("vwap") is not None and current_price >= features["vwap"]:
        return "vwap_hold_reclaim"
    return "high_relative_volume_breakout"


def _strategy_segment(strategy, catalyst):
    return f"{strategy}|{catalyst.get('catalyst_type') or 'unknown'}"


def _apply_segment_policy(strategy, catalyst, market_context, reject_reasons, warnings):
    catalyst_type = catalyst.get("catalyst_type") or "unknown"
    tags = []
    if catalyst.get("signal") == "bearish":
        reject_reasons.append("bearish_catalyst_requires_short_model")
        warnings.append("short_model_not_implemented")
    if (strategy, catalyst_type) in RESEARCH_SUPPORTED_SEGMENTS and catalyst.get("signal") != "bearish":
        tags.append("segment_edge_candidate")
    if _research_evidence(strategy, catalyst, market_context) and catalyst.get("signal") != "bearish":
        tags.append("market_context_edge_candidate")
    if catalyst_type == "unknown":
        warnings.append("unknown_catalyst_requires_confirmation")
    return tags


def _research_evidence(strategy, catalyst, market_context):
    catalyst_type = catalyst.get("catalyst_type") or "unknown"
    risk_context = market_context.get("risk_context") or "unknown"
    return RESEARCH_SUPPORTED_MARKET_CONTEXT_SEGMENTS.get((strategy, catalyst_type, risk_context))


def _calculate_score(features, catalyst, market_context, strategy):
    score = 0
    score += min(catalyst.get("score", 0), 35)
    score += min((features.get("gap_percent") or 0) * 2, 15)
    score += min((features.get("relative_volume") or 0) * 5, 15)
    score += min((features.get("liquidity_score") or 0) * 0.2, 20)
    if market_context.get("risk_context") == "supportive":
        score += 10
    elif market_context.get("risk_context") == "risk_off":
        score -= 10
    if strategy == "opening_range_breakout":
        score += 31
    chart_pattern = features.get("chart_pattern")
    if chart_pattern:
        direction = chart_pattern.get("direction")
        if direction == "bullish":
            score += 5
        elif direction == "bearish":
            score -= 5
    return max(0, min(round(score), 100))


def _status(setup_score, reject_reasons, warnings, actionable_score_threshold=70):
    if reject_reasons:
        return "no_trade"
    if "market_context_risk_off" in warnings:
        return "caution"
    if setup_score >= actionable_score_threshold:
        return "active_watch"
    return "no_trade"


def _confidence(setup_score):
    if setup_score >= 85:
        return "high"
    if setup_score >= 70:
        return "medium_high"
    if setup_score >= 50:
        return "medium"
    return "low"


def _entry_trigger(strategy):
    if strategy == "catalyst_momentum_gap_and_go":
        return "break_above_intraday_high_or_clean_vwap_hold"
    if strategy == "opening_range_breakout":
        return "break_above_opening_range_high"
    if strategy == "vwap_hold_reclaim":
        return "vwap_hold_or_reclaim"
    return "breakout_with_relative_volume_confirmation"
