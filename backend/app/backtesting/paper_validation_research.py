from app.backtesting.batch import run_historical_batch
from app.backtesting.research_report import build_batch_research_report
from app.backtesting.threshold_sweep import DEFAULT_SCORE_THRESHOLDS, sweep_score_thresholds, tune_thresholds_by_segment
from app.features.market_context import summarize_market_context
from app.universe.presets import resolve_universe_preset


async def run_paper_validation_research(
    market_data_provider,
    start,
    end,
    universe_preset="liquid_research_100",
    tickers=None,
    catalysts_by_ticker=None,
    include_news_catalysts=False,
    include_market_context=False,
    lookback_bars=20,
    horizon_bars=5,
    catalyst_max_age_minutes=None,
    actionable_score_threshold=30,
    thresholds=None,
    min_trades=5,
    paper_account_equity=100_000,
    paper_risk_fraction=0.01,
):
    resolved_tickers = _resolve_tickers(tickers or [], universe_preset)
    catalysts_by_ticker = dict(catalysts_by_ticker or {})
    news_catalysts_fetched = 0
    if include_news_catalysts:
        fetched = await _fetch_news_catalysts(resolved_tickers, start, end, market_data_provider)
        for ticker, catalysts in fetched.items():
            catalysts_by_ticker[ticker] = [*catalysts_by_ticker.get(ticker, []), *catalysts]
            news_catalysts_fetched += len(catalysts)

    market_context, market_context_by_timestamp = await _resolve_market_context(
        include_market_context, start, end, market_data_provider
    )
    batch_result = await run_historical_batch(
        tickers=resolved_tickers,
        market_data_provider=market_data_provider,
        start=start,
        end=end,
        catalysts_by_ticker=catalysts_by_ticker,
        market_context=market_context,
        market_context_by_timestamp=market_context_by_timestamp,
        lookback_bars=lookback_bars,
        horizon_bars=horizon_bars,
        catalyst_max_age_minutes=catalyst_max_age_minutes,
        actionable_score_threshold=actionable_score_threshold,
        include_paper_validation=True,
        paper_account_equity=paper_account_equity,
        paper_risk_fraction=paper_risk_fraction,
    )
    items = [item for ticker_result in batch_result["results"].values() for item in ticker_result["items"]]
    thresholds = list(thresholds or DEFAULT_SCORE_THRESHOLDS)
    batch_result["aggregate_threshold_sweep"] = sweep_score_thresholds(
        items, thresholds=thresholds, min_trades=min_trades
    )
    batch_result["aggregate_threshold_tuning_by_segment"] = tune_thresholds_by_segment(
        items, thresholds=thresholds, min_trades=min_trades
    )
    batch_result["research_report"] = build_batch_research_report(batch_result)

    return {
        "run_type": "phase_3_paper_validation_research",
        "universe_preset": universe_preset,
        "orders_enabled": False,
        "start": start,
        "end": end,
        "tickers_total": batch_result["tickers_total"],
        "tickers_completed": batch_result["tickers_completed"],
        "tickers_failed": batch_result["tickers_failed"],
        "evaluated_bars_total": batch_result["evaluated_bars_total"],
        "errors": batch_result["errors"],
        "news_catalysts_fetched": news_catalysts_fetched,
        "market_context_source": "provider_etfs" if include_market_context else "none",
        "paper_validation": _paper_validation_summary(batch_result["paper_validation"]),
        "aggregate_threshold_sweep": batch_result["aggregate_threshold_sweep"],
        "aggregate_threshold_tuning_by_segment": batch_result["aggregate_threshold_tuning_by_segment"],
        "research_report": batch_result["research_report"],
    }


def _resolve_tickers(tickers, universe_preset):
    resolved = [ticker.upper() for ticker in tickers]
    if universe_preset:
        resolved = [*resolved, *resolve_universe_preset(universe_preset)]
    return list(dict.fromkeys(resolved))


async def _fetch_news_catalysts(tickers, start, end, market_data_provider):
    if not hasattr(market_data_provider, "get_news"):
        raise ValueError("Configured provider does not support news catalysts")
    return {ticker: await market_data_provider.get_news(ticker, start, end) for ticker in tickers}


async def _resolve_market_context(include_market_context, start, end, market_data_provider):
    if not include_market_context:
        return {}, None
    etf_candles = {
        symbol: await market_data_provider.get_daily_candles(symbol, start, end)
        for symbol in ["SPY", "QQQ", "IWM"]
    }
    context_by_timestamp = _market_context_by_timestamp(etf_candles)
    latest_timestamp = max(context_by_timestamp) if context_by_timestamp else None
    latest_context = context_by_timestamp.get(latest_timestamp, summarize_market_context(etf_candles))
    return latest_context, context_by_timestamp


def _market_context_by_timestamp(etf_candles):
    timestamps = sorted(
        {
            candle.get("timestamp_ms")
            for candles in etf_candles.values()
            for candle in candles
            if candle.get("timestamp_ms") is not None
        }
    )
    return {
        timestamp: summarize_market_context(
            {
                symbol: [candle for candle in candles if (candle.get("timestamp_ms") or 0) <= timestamp]
                for symbol, candles in etf_candles.items()
            }
        )
        for timestamp in timestamps
    }


def _paper_validation_summary(paper_validation):
    return {
        "mode": "paper_simulation",
        "orders_enabled": False,
        "data_source": "historical_backtest",
        "summary": paper_validation.get("summary", {}),
        "by_evidence_bucket": paper_validation.get("by_evidence_bucket", {}),
        "by_market_context_segment": paper_validation.get("by_market_context_segment", {}),
    }
