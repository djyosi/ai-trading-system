DEFAULT_SCORE_THRESHOLDS = [30, 40, 50, 60, 70, 80, 85, 90]


def sweep_score_thresholds(items, thresholds=None, min_trades=1, min_expectancy_r=0):
    thresholds = thresholds or DEFAULT_SCORE_THRESHOLDS
    rows = [_metrics_for_threshold(items, threshold) for threshold in thresholds]
    eligible = [
        row
        for row in rows
        if row["trade_count"] >= min_trades
        and row["expectancy_r"] is not None
        and row["expectancy_r"] > min_expectancy_r
    ]
    best = max(eligible, key=lambda row: (row["expectancy_r"], row["win_rate"] or 0, row["threshold"]), default=None)
    return {"thresholds": rows, "best_threshold": best, "min_trades": min_trades}


def tune_thresholds_by_segment(items, thresholds=None, min_trades=1):
    grouped = {}
    for item in items:
        recommendation = item.get("recommendation") or {}
        strategy = recommendation.get("strategy") or "unknown"
        catalyst = ((recommendation.get("inputs") or {}).get("catalyst") or {}).get("catalyst_type", "unknown")
        grouped.setdefault(f"{strategy}|{catalyst}", []).append(item)
    return {
        segment: sweep_score_thresholds(segment_items, thresholds=thresholds, min_trades=min_trades)
        for segment, segment_items in sorted(grouped.items())
    }


def _metrics_for_threshold(items, threshold):
    selected = [item for item in items if _is_actionable_closed_at_or_above(item, threshold)]
    realized = [(item.get("outcome") or {}).get("realized_r") for item in selected]
    realized = [value for value in realized if value is not None]
    wins = sum(1 for item in selected if _is_win(item.get("outcome") or {}))
    return {
        "threshold": threshold,
        "trade_count": len(selected),
        "wins": wins,
        "win_rate": _safe_rate(wins, len(selected)),
        "average_realized_r": _average(realized),
        "expectancy_r": _average(realized),
    }


def _is_actionable_closed_at_or_above(item, threshold):
    recommendation = item.get("recommendation") or {}
    outcome = item.get("outcome") or {}
    return (
        recommendation.get("status") != "no_trade"
        and outcome.get("status") == "closed"
        and (recommendation.get("setup_score") or 0) >= threshold
    )


def _is_win(outcome):
    return bool(outcome.get("target_hit") or ((outcome.get("realized_r") or 0) > 0))


def _average(values):
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _safe_rate(numerator, denominator):
    if denominator == 0:
        return None
    return round(numerator / denominator, 2)
