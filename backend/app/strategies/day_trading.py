from app.features.sectors import get_sector

MIN_PRICE = 5
MIN_LIQUIDITY_SCORE = 60
MAX_SPREAD_PERCENT = 0.75
RESEARCH_SUPPORTED_SEGMENTS = {
    ("vwap_hold_reclaim", "contract_win"),
    ("vwap_hold_reclaim", "fda_approval"),
    ("vwap_hold_reclaim", "investigation"),
    ("vwap_hold_reclaim", "analyst_upgrade"),
    ("catalyst_momentum_gap_and_go", "analyst_upgrade"),
}
RESEARCH_SUPPORTED_MARKET_CONTEXT_SEGMENTS = {
    ("vwap_hold_reclaim", "contract_win", "risk_off"): {
        "market_context_segment": "vwap_hold_reclaim|contract_win|risk_off",
        "recommended_threshold": 50,
        "trade_count": 13,
        "win_rate": 0.69,
        "expectancy_r": 0.73,
    },
    ("vwap_hold_reclaim", "fda_approval", "mixed"): {
        "market_context_segment": "vwap_hold_reclaim|fda_approval|mixed",
        "recommended_threshold": 60,
        "trade_count": 7,
        "win_rate": 0.57,
        "expectancy_r": 0.43,
    },
    ("vwap_hold_reclaim", "investigation", "mixed"): {
        "market_context_segment": "vwap_hold_reclaim|investigation|mixed",
        "recommended_threshold": 30,
        "trade_count": 7,
        "win_rate": 0.71,
        "expectancy_r": 0.79,
    },
    ("vwap_hold_reclaim", "analyst_upgrade", "mixed"): {
        "market_context_segment": "vwap_hold_reclaim|analyst_upgrade|mixed",
        "recommended_threshold": 60,
        "trade_count": 8,
        "win_rate": 0.50,
        "expectancy_r": 0.20,
    },
    ("catalyst_momentum_gap_and_go", "analyst_upgrade", "supportive"): {
        "market_context_segment": "catalyst_momentum_gap_and_go|analyst_upgrade|supportive",
        "recommended_threshold": 85,
        "trade_count": 5,
        "win_rate": 0.60,
        "expectancy_r": 0.50,
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
    setup_score = _calculate_score(features, catalyst, market_context, strategy, ticker)
    status = _status(setup_score, reject_reasons, warnings, actionable_score_threshold, research_evidence)

    return {
        "ticker": ticker,
        "sector": _sector(ticker),
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
        "chart_pattern": features.get("chart_pattern"),
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


def _calculate_score(features, catalyst, market_context, strategy, ticker=None):
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
        strength = chart_pattern.get("strength")
        boost = {"weak": 3, "moderate": 5, "strong": 8}.get(strength, 5)
        if direction == "bullish":
            score += boost
        elif direction == "bearish":
            score -= boost
    sector = _sector(ticker)
    if sector == "utilities":
        score += 5
    elif sector == "energy":
        score += 3
    elif sector == "unknown":
        score -= 3
    return max(0, min(round(score), 100))


def _status(setup_score, reject_reasons, warnings, actionable_score_threshold=70, research_evidence=None):
    if reject_reasons:
        return "no_trade"
    if "market_context_risk_off" in warnings:
        return "caution"
    segment_threshold = (research_evidence or {}).get("recommended_threshold")
    effective_threshold = min(actionable_score_threshold, segment_threshold) if segment_threshold else actionable_score_threshold
    if setup_score >= effective_threshold:
        return "active_watch"
    return "no_trade"


def _sector(ticker):
    return get_sector(ticker)


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
