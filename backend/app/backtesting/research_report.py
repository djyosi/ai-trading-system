from app.backtesting.threshold_sweep import sweep_score_thresholds


def build_batch_research_report(batch_result, top_n=5):
    warnings = []
    coverage = {
        "tickers_total": batch_result.get("tickers_total", 0),
        "tickers_completed": batch_result.get("tickers_completed", 0),
        "tickers_failed": batch_result.get("tickers_failed", 0),
        "evaluated_bars_total": batch_result.get("evaluated_bars_total", 0),
    }
    if coverage["tickers_failed"]:
        warnings.append(f"{coverage['tickers_failed']} ticker(s) failed")

    threshold_sweep = batch_result.get("aggregate_threshold_sweep") or {}
    best_threshold = threshold_sweep.get("best_threshold")
    if best_threshold is None:
        min_trades = threshold_sweep.get("min_trades")
        if min_trades is not None:
            warnings.append(f"No threshold met both minimum trades ({min_trades}) and positive expectancy")

    symbol_rows = [_symbol_row(ticker, result) for ticker, result in sorted((batch_result.get("results") or {}).items())]
    top_symbols = sorted(
        [row for row in symbol_rows if row["expectancy_r"] is not None],
        key=lambda row: (row["expectancy_r"], row["closed_total"], row["ticker"]),
        reverse=True,
    )[:top_n]
    weak_symbols = sorted(
        [row for row in symbol_rows if row["expectancy_r"] is not None and row["expectancy_r"] <= 0],
        key=lambda row: (row["expectancy_r"], row["ticker"]),
    )[:top_n]

    top_segments = _top_segments(batch_result.get("aggregate_threshold_tuning_by_segment") or {}, top_n)
    segment_threshold_recommendations = top_segments
    market_context_segment_recommendations = _market_context_segment_recommendations(
        batch_result.get("results") or {},
        min_trades=threshold_sweep.get("min_trades", 1),
        top_n=top_n,
    )
    recommendation_diagnostics = _recommendation_diagnostics(batch_result.get("results") or {})
    ticker_diagnostics = _ticker_diagnostics(batch_result.get("results") or {}, top_n)
    edge_diagnostics = _edge_diagnostics(batch_result.get("results") or {}, top_n)
    next_research_actions = _next_research_actions(threshold_sweep, edge_diagnostics)
    _append_actionability_warnings(warnings, recommendation_diagnostics)

    return {
        "status": "research_ready" if best_threshold is not None else "needs_more_data",
        "coverage": coverage,
        "recommended_threshold": best_threshold.get("threshold") if best_threshold else None,
        "best_threshold": best_threshold,
        "top_symbols": top_symbols,
        "weak_symbols": weak_symbols,
        "top_segments": top_segments,
        "segment_threshold_recommendations": segment_threshold_recommendations,
        "market_context_segment_recommendations": market_context_segment_recommendations,
        "recommendation_diagnostics": recommendation_diagnostics,
        "ticker_diagnostics": ticker_diagnostics,
        "edge_diagnostics": edge_diagnostics,
        "next_research_actions": next_research_actions,
        "warnings": warnings,
    }


def _edge_diagnostics(results, top_n):
    closed_items = []
    for result in results.values():
        for item in result.get("items", []):
            recommendation = item.get("recommendation") or {}
            outcome = item.get("outcome") or {}
            if recommendation.get("status") == "no_trade" or outcome.get("status") != "closed":
                continue
            closed_items.append(item)
    return {
        "score_bands": _summarize_edge_segments(closed_items, _score_band, top_n=top_n),
        "catalyst_types": _summarize_edge_segments(closed_items, _catalyst_type, top_n=top_n),
        "market_contexts": _summarize_edge_segments(closed_items, _risk_context, top_n=top_n),
    }


def _summarize_edge_segments(items, key_fn, top_n):
    groups = {}
    for item in items:
        key = key_fn(item)
        outcome = item.get("outcome") or {}
        realized_r = outcome.get("realized_r")
        if realized_r is None:
            continue
        groups.setdefault(key, []).append(outcome)
    rows = []
    for segment, outcomes in sorted(groups.items()):
        realized_values = [outcome.get("realized_r") for outcome in outcomes]
        wins = sum(1 for outcome in outcomes if outcome.get("target_hit") or (outcome.get("realized_r") or 0) > 0)
        rows.append(
            {
                "segment": segment,
                "trade_count": len(outcomes),
                "wins": wins,
                "win_rate": round(wins / len(outcomes), 2) if outcomes else None,
                "expectancy_r": round(sum(realized_values) / len(realized_values), 2),
            }
        )
    return sorted(rows, key=lambda row: (row["expectancy_r"], row["trade_count"], row["segment"]), reverse=True)[:top_n]


def _score_band(item):
    score = ((item.get("recommendation") or {}).get("setup_score") or 0)
    lower = int(score // 10) * 10
    upper = lower + 9
    return f"{lower}-{upper}"


def _catalyst_type(item):
    recommendation = item.get("recommendation") or {}
    return (((recommendation.get("inputs") or {}).get("catalyst") or {}).get("catalyst_type")) or "unknown"


def _risk_context(item):
    recommendation = item.get("recommendation") or {}
    return (((recommendation.get("inputs") or {}).get("market_context") or {}).get("risk_context")) or "unknown"


def _next_research_actions(threshold_sweep, edge_diagnostics):
    actions = []
    if threshold_sweep.get("best_threshold") is None and threshold_sweep.get("min_trades") is not None:
        actions.append(
            {
                "action": "increase_sample_size",
                "reason": "No global threshold met minimum trades and positive expectancy",
                "min_trades": threshold_sweep.get("min_trades"),
            }
        )
    actions.extend(_promising_sparse_segment_actions(edge_diagnostics))
    actions.extend(_weak_segment_actions(edge_diagnostics))
    return actions


def _promising_sparse_segment_actions(edge_diagnostics, max_trade_count=3):
    actions = []
    for dimension, rows in edge_diagnostics.items():
        for row in rows:
            expectancy = row.get("expectancy_r")
            trade_count = row.get("trade_count", 0)
            if expectancy is None or expectancy <= 0 or trade_count > max_trade_count:
                continue
            actions.append(
                {
                    "action": "investigate_promising_segment",
                    "dimension": dimension,
                    "segment": row.get("segment"),
                    "reason": f"Positive expectancy but only {trade_count} closed trade(s)",
                    "trade_count": trade_count,
                    "expectancy_r": expectancy,
                }
            )
    return actions[:1]


def _weak_segment_actions(edge_diagnostics, min_trade_count=2):
    actions = []
    dimension_priority = {"catalyst_types": 0, "score_bands": 1, "market_contexts": 2}
    for dimension, rows in edge_diagnostics.items():
        for row in rows:
            expectancy = row.get("expectancy_r")
            trade_count = row.get("trade_count", 0)
            if expectancy is None or expectancy >= 0 or trade_count < min_trade_count:
                continue
            actions.append(
                {
                    "action": "deprioritize_segment",
                    "dimension": dimension,
                    "segment": row.get("segment"),
                    "reason": "Negative expectancy segment",
                    "trade_count": trade_count,
                    "expectancy_r": expectancy,
                }
            )
    return sorted(actions, key=lambda action: dimension_priority.get(action["dimension"], 99))[:1]


def _append_actionability_warnings(warnings, diagnostics, min_actionable_rate=0.5):
    total = diagnostics.get("total_recommendations", 0)
    if not total:
        return
    actionable = diagnostics.get("actionable_total", 0)
    actionable_rate = actionable / total
    if actionable_rate >= min_actionable_rate:
        return
    warnings.append(f"Low actionability: {actionable}/{total} recommendations were actionable ({actionable_rate:.2%})")
    no_trade_reasons = diagnostics.get("no_trade_reasons") or []
    if no_trade_reasons:
        top_reason = no_trade_reasons[0]
        warnings.append(f"Most common no-trade reason: {top_reason['reason']} ({top_reason['count']})")


def _ticker_diagnostics(results, top_n):
    rows = []
    for ticker, result in sorted(results.items()):
        diagnostics = _items_diagnostics(result.get("items", []), include_rates=True)
        rows.append({"ticker": ticker, **diagnostics})
    return sorted(
        rows,
        key=lambda row: (row["actionable_rate"], -row["no_trade_total"], row["ticker"]),
    )[:top_n]


def _recommendation_diagnostics(results):
    aggregate_items = []
    for result in results.values():
        aggregate_items.extend(result.get("items", []))
    return _items_diagnostics(aggregate_items, include_reasons=True)


def _items_diagnostics(items, include_reasons=False, include_rates=False):
    total = 0
    no_trade_total = 0
    reasons = {}
    for item in items:
        recommendation = item.get("recommendation") or {}
        total += 1
        if recommendation.get("status") != "no_trade":
            continue
        no_trade_total += 1
        for reason in recommendation.get("reject_reasons") or ["score_below_actionable_threshold"]:
            reasons[reason] = reasons.get(reason, 0) + 1
    reason_rows = [
        {"reason": reason, "count": count} for reason, count in sorted(reasons.items(), key=lambda item: (-item[1], item[0]))
    ]
    diagnostics = {
        "total_recommendations": total,
        "actionable_total": total - no_trade_total,
        "no_trade_total": no_trade_total,
    }
    if include_rates:
        diagnostics["actionable_rate"] = round((total - no_trade_total) / total, 4) if total else 0.0
        diagnostics["top_no_trade_reason"] = reason_rows[0]["reason"] if reason_rows else None
    if include_reasons:
        diagnostics["no_trade_reasons"] = reason_rows
    return diagnostics


def _market_context_segment_recommendations(results, min_trades, top_n):
    groups = {}
    for result in results.values():
        for item in result.get("items", []):
            recommendation = item.get("recommendation") or {}
            inputs = recommendation.get("inputs") or {}
            strategy = recommendation.get("strategy") or "unknown"
            catalyst = ((inputs.get("catalyst") or {}).get("catalyst_type")) or "unknown"
            market_context = ((inputs.get("market_context") or {}).get("risk_context")) or "unknown"
            groups.setdefault(f"{strategy}|{catalyst}|{market_context}", []).append(item)

    rows = []
    for segment, items in sorted(groups.items()):
        best_threshold = sweep_score_thresholds(items, min_trades=min_trades).get("best_threshold")
        if not best_threshold:
            continue
        strategy, catalyst_type, market_context = _split_market_context_segment(segment)
        rows.append(
            {
                "segment": segment,
                "strategy": strategy,
                "catalyst_type": catalyst_type,
                "market_context": market_context,
                "recommended_threshold": best_threshold.get("threshold"),
                "trade_count": best_threshold.get("trade_count", 0),
                "expectancy_r": best_threshold.get("expectancy_r"),
                "win_rate": best_threshold.get("win_rate"),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["expectancy_r"] if row["expectancy_r"] is not None else float("-inf"),
            row["trade_count"],
            row["segment"],
        ),
        reverse=True,
    )[:top_n]


def _split_market_context_segment(segment):
    parts = segment.split("|", 2)
    if len(parts) == 1:
        return parts[0], "unknown", "unknown"
    if len(parts) == 2:
        return parts[0], parts[1], "unknown"
    return parts[0], parts[1], parts[2]


def _top_segments(segment_tuning, top_n):
    rows = []
    for segment, data in sorted(segment_tuning.items()):
        best_threshold = (data or {}).get("best_threshold")
        if not best_threshold:
            continue
        strategy, catalyst_type = _split_segment(segment)
        rows.append(
            {
                "segment": segment,
                "strategy": strategy,
                "catalyst_type": catalyst_type,
                "recommended_threshold": best_threshold.get("threshold"),
                "trade_count": best_threshold.get("trade_count", 0),
                "expectancy_r": best_threshold.get("expectancy_r"),
                "win_rate": best_threshold.get("win_rate"),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["expectancy_r"] if row["expectancy_r"] is not None else float("-inf"),
            row["trade_count"],
            row["segment"],
        ),
        reverse=True,
    )[:top_n]


def _split_segment(segment):
    if "|" not in segment:
        return segment, "unknown"
    strategy, catalyst_type = segment.split("|", 1)
    return strategy, catalyst_type


def _symbol_row(ticker, result):
    summary = result.get("summary") or {}
    return {
        "ticker": ticker,
        "evaluated_total": summary.get("evaluated_total", result.get("evaluated_bars", 0)),
        "closed_total": summary.get("closed_total", 0),
        "win_rate": summary.get("win_rate"),
        "expectancy_r": summary.get("expectancy_r"),
        "average_realized_r": summary.get("average_realized_r"),
    }
