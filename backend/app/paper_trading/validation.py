from app.paper_trading.simulator import simulate_paper_trade


def validate_paper_recommendations(items, account_equity=100_000, risk_fraction=0.01):
    validated_items = []
    for item in items:
        recommendation = item.get("recommendation") or {}
        paper_result = simulate_paper_trade(
            recommendation,
            item.get("candles") or [],
            account_equity=account_equity,
            risk_fraction=risk_fraction,
        )
        validated_items.append({"recommendation": recommendation, "paper_result": paper_result})

    return {
        "summary": _summary(validated_items),
        "by_evidence_bucket": _grouped(validated_items, _evidence_bucket),
        "by_market_context_segment": _grouped(validated_items, _market_context_segment, skip_none=True),
        "items": validated_items,
    }


def _grouped(items, key_fn, skip_none=False):
    groups = {}
    for item in items:
        key = key_fn(item)
        if key is None and skip_none:
            continue
        groups.setdefault(key, []).append(item)
    return {key: _summary(group_items) for key, group_items in sorted(groups.items())}


def _evidence_bucket(item):
    recommendation = item.get("recommendation") or {}
    tags = recommendation.get("research_tags") or []
    if "market_context_edge_candidate" in tags and recommendation.get("research_evidence"):
        return "evidence_backed"
    return "baseline"


def _market_context_segment(item):
    recommendation = item.get("recommendation") or {}
    evidence = recommendation.get("research_evidence") or {}
    return evidence.get("market_context_segment")


def _summary(items):
    results = [item.get("paper_result") or {} for item in items]
    closed = [result for result in results if result.get("status") == "closed"]
    realized_values = [result.get("realized_r") for result in closed if result.get("realized_r") is not None]
    wins = sum(1 for result in closed if (result.get("realized_r") or 0) > 0 or result.get("exit_reason") == "target_hit")
    losses = sum(1 for result in closed if (result.get("realized_r") or 0) < 0 or result.get("exit_reason") == "stop_hit")
    return {
        "recommendations_total": len(results),
        "closed_total": len(closed),
        "skipped_total": sum(1 for result in results if result.get("status") == "skipped"),
        "not_triggered_total": sum(1 for result in results if result.get("status") == "not_triggered"),
        "wins": wins,
        "losses": losses,
        "win_rate": _safe_rate(wins, len(closed)),
        "average_realized_r": _average(realized_values),
        "expectancy_r": _average(realized_values),
    }


def _average(values):
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _safe_rate(numerator, denominator):
    if denominator == 0:
        return None
    return round(numerator / denominator, 2)
