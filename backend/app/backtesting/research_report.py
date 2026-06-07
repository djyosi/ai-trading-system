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

    return {
        "status": "research_ready" if best_threshold is not None else "needs_more_data",
        "coverage": coverage,
        "recommended_threshold": best_threshold.get("threshold") if best_threshold else None,
        "best_threshold": best_threshold,
        "top_symbols": top_symbols,
        "weak_symbols": weak_symbols,
        "warnings": warnings,
    }


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
