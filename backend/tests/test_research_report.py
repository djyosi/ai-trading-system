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


def test_batch_research_report_surfaces_segment_threshold_recommendations_even_when_global_not_ready():
    batch = {
        "tickers_total": 2,
        "tickers_completed": 2,
        "tickers_failed": 0,
        "evaluated_bars_total": 20,
        "results": {},
        "errors": {},
        "aggregate_threshold_sweep": {"best_threshold": None, "min_trades": 5},
        "aggregate_threshold_tuning_by_segment": {
            "gap_and_go|contract_win": {
                "best_threshold": {"threshold": 60, "trade_count": 5, "expectancy_r": 0.45, "win_rate": 0.6},
                "min_trades": 5,
            },
            "gap_and_go|unknown": {
                "best_threshold": None,
                "min_trades": 5,
            },
        },
    }

    report = build_batch_research_report(batch)

    assert report["status"] == "needs_more_data"
    assert report["segment_threshold_recommendations"] == [
        {
            "segment": "gap_and_go|contract_win",
            "strategy": "gap_and_go",
            "catalyst_type": "contract_win",
            "recommended_threshold": 60,
            "trade_count": 5,
            "expectancy_r": 0.45,
            "win_rate": 0.6,
        }
    ]


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


def test_batch_research_report_summarizes_no_trade_reasons():
    no_trade_items = [
        {"recommendation": {"status": "no_trade", "reject_reasons": ["liquidity_score_below_min"]}},
        {"recommendation": {"status": "no_trade", "reject_reasons": ["price_below_min", "liquidity_score_below_min"]}},
        {"recommendation": {"status": "active_watch", "reject_reasons": []}},
    ]
    batch = {
        "tickers_total": 1,
        "tickers_completed": 1,
        "tickers_failed": 0,
        "evaluated_bars_total": 3,
        "results": {"AAPL": {**_result("AAPL", closed_total=0, expectancy_r=None, win_rate=None), "items": no_trade_items}},
        "errors": {},
        "aggregate_threshold_sweep": {"best_threshold": None, "min_trades": 5},
    }

    report = build_batch_research_report(batch)

    assert report["recommendation_diagnostics"] == {
        "total_recommendations": 3,
        "actionable_total": 1,
        "no_trade_total": 2,
        "no_trade_reasons": [
            {"reason": "liquidity_score_below_min", "count": 2},
            {"reason": "price_below_min", "count": 1},
        ],
    }


def test_batch_research_report_summarizes_ticker_diagnostics():
    aapl_items = [
        {"recommendation": {"status": "no_trade", "reject_reasons": ["liquidity_score_below_min"]}},
        {"recommendation": {"status": "active_watch", "reject_reasons": []}},
    ]
    msft_items = [
        {"recommendation": {"status": "no_trade", "reject_reasons": ["price_below_min"]}},
        {"recommendation": {"status": "no_trade", "reject_reasons": ["price_below_min"]}},
    ]
    batch = {
        "tickers_total": 2,
        "tickers_completed": 2,
        "tickers_failed": 0,
        "evaluated_bars_total": 4,
        "results": {
            "AAPL": {**_result("AAPL", closed_total=1, expectancy_r=0.3, win_rate=1.0), "items": aapl_items},
            "MSFT": {**_result("MSFT", closed_total=0, expectancy_r=None, win_rate=None), "items": msft_items},
        },
        "errors": {},
        "aggregate_threshold_sweep": {"best_threshold": None, "min_trades": 5},
    }

    report = build_batch_research_report(batch)

    assert report["ticker_diagnostics"] == [
        {
            "ticker": "MSFT",
            "total_recommendations": 2,
            "actionable_total": 0,
            "no_trade_total": 2,
            "actionable_rate": 0.0,
            "top_no_trade_reason": "price_below_min",
        },
        {
            "ticker": "AAPL",
            "total_recommendations": 2,
            "actionable_total": 1,
            "no_trade_total": 1,
            "actionable_rate": 0.5,
            "top_no_trade_reason": "liquidity_score_below_min",
        },
    ]


def test_batch_research_report_summarizes_edge_diagnostics_by_score_catalyst_and_market_context():
    items = [
        {
            "recommendation": {
                "status": "active_watch",
                "setup_score": 35,
                "strategy": "gap_and_go",
                "inputs": {
                    "catalyst": {"catalyst_type": "earnings_beat"},
                    "market_context": {"risk_context": "supportive"},
                },
            },
            "outcome": {"status": "closed", "realized_r": 1.5, "target_hit": True},
        },
        {
            "recommendation": {
                "status": "active_watch",
                "setup_score": 52,
                "strategy": "gap_and_go",
                "inputs": {
                    "catalyst": {"catalyst_type": "analyst_upgrade"},
                    "market_context": {"risk_context": "mixed"},
                },
            },
            "outcome": {"status": "closed", "realized_r": -1.0, "stop_hit": True},
        },
        {
            "recommendation": {
                "status": "active_watch",
                "setup_score": 58,
                "strategy": "gap_and_go",
                "inputs": {
                    "catalyst": {"catalyst_type": "analyst_upgrade"},
                    "market_context": {"risk_context": "mixed"},
                },
            },
            "outcome": {"status": "closed", "realized_r": 1.0, "target_hit": True},
        },
        {
            "recommendation": {
                "status": "no_trade",
                "setup_score": 28,
                "inputs": {"catalyst": {"catalyst_type": "unknown"}, "market_context": {"risk_context": "risk_off"}},
            },
            "outcome": {"status": "skipped"},
        },
    ]
    batch = {
        "tickers_total": 1,
        "tickers_completed": 1,
        "tickers_failed": 0,
        "evaluated_bars_total": 4,
        "results": {"AAPL": {**_result("AAPL", closed_total=3, expectancy_r=0.5, win_rate=0.67), "items": items}},
        "errors": {},
        "aggregate_threshold_sweep": {"best_threshold": {"threshold": 50, "trade_count": 2, "expectancy_r": 0.0}, "min_trades": 1},
    }

    report = build_batch_research_report(batch)

    assert report["edge_diagnostics"]["score_bands"] == [
        {"segment": "30-39", "trade_count": 1, "wins": 1, "win_rate": 1.0, "expectancy_r": 1.5},
        {"segment": "50-59", "trade_count": 2, "wins": 1, "win_rate": 0.5, "expectancy_r": 0.0},
    ]
    assert report["edge_diagnostics"]["catalyst_types"] == [
        {"segment": "earnings_beat", "trade_count": 1, "wins": 1, "win_rate": 1.0, "expectancy_r": 1.5},
        {"segment": "analyst_upgrade", "trade_count": 2, "wins": 1, "win_rate": 0.5, "expectancy_r": 0.0},
    ]
    assert report["edge_diagnostics"]["market_contexts"] == [
        {"segment": "supportive", "trade_count": 1, "wins": 1, "win_rate": 1.0, "expectancy_r": 1.5},
        {"segment": "mixed", "trade_count": 2, "wins": 1, "win_rate": 0.5, "expectancy_r": 0.0},
    ]


def test_batch_research_report_warns_when_actionability_is_low():
    items = [
        {"recommendation": {"status": "no_trade", "reject_reasons": ["liquidity_score_below_min"]}},
        {"recommendation": {"status": "no_trade", "reject_reasons": ["score_below_actionable_threshold"]}},
        {"recommendation": {"status": "active_watch", "reject_reasons": []}},
    ]
    batch = {
        "tickers_total": 1,
        "tickers_completed": 1,
        "tickers_failed": 0,
        "evaluated_bars_total": 3,
        "results": {"AAPL": {**_result("AAPL", closed_total=0, expectancy_r=None, win_rate=None), "items": items}},
        "errors": {},
        "aggregate_threshold_sweep": {"best_threshold": None, "min_trades": 5},
    }

    report = build_batch_research_report(batch)

    assert "Low actionability: 1/3 recommendations were actionable (33.33%)" in report["warnings"]
    assert "Most common no-trade reason: liquidity_score_below_min (1)" in report["warnings"]


def test_batch_research_report_warns_when_no_threshold_has_positive_expectancy():
    batch = {
        "tickers_total": 1,
        "tickers_completed": 1,
        "tickers_failed": 0,
        "evaluated_bars_total": 3,
        "results": {"AAPL": {"items": []}},
        "aggregate_threshold_sweep": {
            "min_trades": 3,
            "best_threshold": None,
            "thresholds": [
                {"threshold": 40, "trade_count": 3, "expectancy_r": 0.0},
                {"threshold": 50, "trade_count": 2, "expectancy_r": 1.0},
            ],
        },
    }

    report = build_batch_research_report(batch)

    assert report["status"] == "needs_more_data"
    assert "No threshold met both minimum trades (3) and positive expectancy" in report["warnings"]


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
    assert "No threshold met both minimum trades (5) and positive expectancy" in report["warnings"]
