from app.backtesting.research_report import build_batch_research_report


def _result(ticker, closed_total, expectancy_r, win_rate, evaluated_total=10):
    return {
        "ticker": ticker,
        "evaluated_bars": evaluated_total,
        "summary": {
            "evaluated_total": evaluated_total,
            "closed_total": closed_total,
            "wins": int((win_rate or 0) * closed_total),
            "losses": max(closed_total - int((win_rate or 0) * closed_total), 0),
            "win_rate": win_rate,
            "average_realized_r": expectancy_r,
            "expectancy_r": expectancy_r,
        },
        "items": [],
    }


def test_batch_research_report_ranks_symbols_and_carries_best_threshold():
    batch = {
        "tickers_total": 3,
        "tickers_completed": 2,
        "tickers_failed": 1,
        "evaluated_bars_total": 20,
        "results": {
            "AAPL": _result("AAPL", closed_total=8, expectancy_r=0.45, win_rate=0.62),
            "MSFT": _result("MSFT", closed_total=6, expectancy_r=-0.12, win_rate=0.33),
        },
        "errors": {"FAIL": "provider failed"},
        "aggregate_threshold_sweep": {
            "best_threshold": {"threshold": 80, "trade_count": 9, "expectancy_r": 0.38, "win_rate": 0.67},
            "min_trades": 5,
        },
    }

    report = build_batch_research_report(batch)

    assert report["status"] == "research_ready"
    assert report["coverage"] == {"tickers_total": 3, "tickers_completed": 2, "tickers_failed": 1, "evaluated_bars_total": 20}
    assert report["recommended_threshold"] == 80
    assert report["top_symbols"][0]["ticker"] == "AAPL"
    assert report["top_symbols"][0]["expectancy_r"] == 0.45
    assert report["weak_symbols"][0]["ticker"] == "MSFT"
    assert "1 ticker(s) failed" in report["warnings"]


def test_batch_research_report_ranks_strategy_catalyst_segments():
    batch = {
        "tickers_total": 2,
        "tickers_completed": 2,
        "tickers_failed": 0,
        "evaluated_bars_total": 20,
        "results": {
            "AAPL": _result("AAPL", closed_total=8, expectancy_r=0.45, win_rate=0.62),
            "MSFT": _result("MSFT", closed_total=6, expectancy_r=0.2, win_rate=0.5),
        },
        "errors": {},
        "aggregate_threshold_sweep": {
            "best_threshold": {"threshold": 80, "trade_count": 9, "expectancy_r": 0.38, "win_rate": 0.67},
            "min_trades": 5,
        },
        "aggregate_threshold_tuning_by_segment": {
            "gap_and_go|earnings_beat": {
                "best_threshold": {"threshold": 80, "trade_count": 7, "expectancy_r": 0.55, "win_rate": 0.71}
            },
            "vwap_hold|analyst_upgrade": {
                "best_threshold": {"threshold": 70, "trade_count": 5, "expectancy_r": 0.25, "win_rate": 0.6}
            },
            "gap_and_go|unknown": {"best_threshold": None},
        },
    }

    report = build_batch_research_report(batch)

    assert report["top_segments"] == [
        {
            "segment": "gap_and_go|earnings_beat",
            "strategy": "gap_and_go",
            "catalyst_type": "earnings_beat",
            "recommended_threshold": 80,
            "trade_count": 7,
            "expectancy_r": 0.55,
            "win_rate": 0.71,
        },
        {
            "segment": "vwap_hold|analyst_upgrade",
            "strategy": "vwap_hold",
            "catalyst_type": "analyst_upgrade",
            "recommended_threshold": 70,
            "trade_count": 5,
            "expectancy_r": 0.25,
            "win_rate": 0.6,
        },
    ]


def test_batch_research_report_flags_insufficient_threshold_sample():
    batch = {
        "tickers_total": 1,
        "tickers_completed": 1,
        "tickers_failed": 0,
        "evaluated_bars_total": 10,
        "results": {"AAPL": _result("AAPL", closed_total=0, expectancy_r=None, win_rate=None)},
        "errors": {},
        "aggregate_threshold_sweep": {"best_threshold": None, "min_trades": 5},
    }

    report = build_batch_research_report(batch)

    assert report["status"] == "needs_more_data"
    assert report["recommended_threshold"] is None
    assert "No threshold met the minimum trade requirement of 5" in report["warnings"]
