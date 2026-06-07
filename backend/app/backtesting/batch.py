from app.backtesting.walk_forward import run_walk_forward_replay


async def run_historical_batch(
    tickers,
    market_data_provider,
    start,
    end,
    catalysts_by_ticker=None,
    market_context=None,
    lookback_bars=20,
    horizon_bars=5,
    catalyst_max_age_minutes=None,
    actionable_score_threshold=70,
):
    catalysts_by_ticker = catalysts_by_ticker or {}
    results = {}
    errors = {}

    for ticker in tickers:
        try:
            candles = await market_data_provider.get_daily_candles(ticker, start, end)
            results[ticker] = run_walk_forward_replay(
                ticker=ticker,
                candles=candles,
                catalysts=catalysts_by_ticker.get(ticker, []),
                market_context=market_context,
                lookback_bars=lookback_bars,
                horizon_bars=horizon_bars,
                catalyst_max_age_minutes=catalyst_max_age_minutes,
                actionable_score_threshold=actionable_score_threshold,
            )
        except Exception as exc:  # noqa: BLE001 - batch jobs must isolate per-symbol provider failures
            errors[ticker] = str(exc)

    return {
        "tickers_total": len(tickers),
        "tickers_completed": len(results),
        "tickers_failed": len(errors),
        "evaluated_bars_total": sum(result["evaluated_bars"] for result in results.values()),
        "results": results,
        "errors": errors,
    }
