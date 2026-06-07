from app.strategies.day_trading import score_day_trade_setup


def build_recommendation(ticker, features, catalyst, market_context, actionable_score_threshold=70):
    strategy_result = score_day_trade_setup(
        ticker,
        features,
        catalyst,
        market_context,
        actionable_score_threshold=actionable_score_threshold,
    )
    status = strategy_result["status"]

    trade_plan = _build_trade_plan(features, status)

    recommendation = {
        "ticker": ticker,
        "timeframe": "day_trade",
        "direction": strategy_result["direction"],
        "status": status,
        "setup_score": strategy_result["setup_score"],
        "confidence": strategy_result["confidence"],
        "strategy": strategy_result["strategy"],
        "strategy_segment": strategy_result["strategy_segment"],
        "research_tags": strategy_result["research_tags"],
        "entry_trigger": strategy_result["entry_trigger"],
        "entry_zone": trade_plan["entry_zone"],
        "stop_loss": trade_plan["stop_loss"],
        "targets": trade_plan["targets"],
        "risk_reward": trade_plan["risk_reward"],
        "invalid_if": strategy_result["invalid_if"],
        "reject_reasons": strategy_result["reject_reasons"],
        "warnings": strategy_result["warnings"],
        "reason": _build_reason(strategy_result, features, catalyst, market_context),
        "inputs": {
            "features": features,
            "catalyst": catalyst,
            "market_context": market_context,
        },
    }
    return recommendation


def _build_trade_plan(features, status):
    if status == "no_trade":
        return {"entry_zone": None, "stop_loss": None, "targets": [], "risk_reward": None}

    current_price = features.get("current_price") or features.get("price")
    if not current_price:
        return {"entry_zone": None, "stop_loss": None, "targets": [], "risk_reward": None}

    stop_basis = features.get("vwap") or current_price * 0.97
    atr_percent = features.get("atr_percent") or 3.0
    stop_loss = round(min(stop_basis * 0.99, current_price * (1 - atr_percent / 100)), 2)
    risk_per_share = max(current_price - stop_loss, 0.01)

    entry_zone = [round(current_price * 0.99, 2), round(current_price * 1.01, 2)]
    targets = [round(current_price + risk_per_share * 1.5, 2), round(current_price + risk_per_share * 2.6, 2)]
    risk_reward = round((targets[0] - current_price) / risk_per_share, 2)

    return {
        "entry_zone": entry_zone,
        "stop_loss": stop_loss,
        "targets": targets,
        "risk_reward": risk_reward,
    }


def _build_reason(strategy_result, features, catalyst, market_context):
    if strategy_result["status"] == "no_trade":
        return "No trade: " + ", ".join(strategy_result["reject_reasons"])

    parts = []
    if catalyst.get("signal") == "bullish" and catalyst.get("score", 0) >= 60:
        parts.append(f"Strong bullish catalyst ({catalyst.get('catalyst_type')})")
    elif catalyst.get("signal") == "bearish":
        parts.append(f"Bearish catalyst ({catalyst.get('catalyst_type')})")
    else:
        parts.append("Technical setup without a strong catalyst")

    if "segment_edge_candidate" in strategy_result.get("research_tags", []):
        parts.append("research-supported segment")
    if features.get("gap_percent") is not None:
        parts.append(f"gap {features['gap_percent']}%")
    if features.get("relative_volume") is not None:
        parts.append(f"relative volume {features['relative_volume']}x")
    if features.get("liquidity_score") is not None:
        parts.append(f"liquidity score {features['liquidity_score']}")
    if market_context.get("risk_context") == "risk_off":
        parts.append("risk-off market context")
    elif market_context.get("risk_context") == "supportive":
        parts.append("supportive market context")

    return "; ".join(parts) + "."
