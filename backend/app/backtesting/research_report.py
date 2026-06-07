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
            warnings.append(f"No threshold met the minimum trade requirement of {min_trades}")

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
    recommendation_diagnostics = _recommendation_diagnostics(batch_result.get("results") or {})
    ticker_diagnostics = _ticker_diagnostics(batch_result.get("results") or {}, top_n)

    return {
        "status": "research_ready" if best_threshold is not None else "needs_more_data",
        "coverage": coverage,
        "recommended_threshold": best_threshold.get("threshold") if best_threshold else None,
        "best_threshold": best_threshold,
        "top_symbols": top_symbols,
        "weak_symbols": weak_symbols,
        "top_segments": top_segments,
        "recommendation_diagnostics": recommendation_diagnostics,
        "ticker_diagnostics": ticker_diagnostics,
        "warnings": warnings,
    }


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
