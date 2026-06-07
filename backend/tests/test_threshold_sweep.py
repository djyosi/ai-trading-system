from app.backtesting.threshold_sweep import sweep_score_thresholds, tune_thresholds_by_segment


def _item(score, realized_r, strategy="gap_and_go", catalyst_type="earnings_beat", status="active_watch"):
    return {
        "recommendation": {
            "setup_score": score,
            "status": status,
            "strategy": strategy,
            "inputs": {"catalyst": {"catalyst_type": catalyst_type}},
        },
        "outcome": {
            "status": "closed",
            "realized_r": realized_r,
            "target_hit": realized_r > 0,
            "stop_hit": realized_r < 0,
        },
    }


def test_sweep_score_thresholds_default_thresholds_include_research_candidate_scores():
    items = [_item(32, 1.0), _item(41, -1.0), _item(72, 2.0)]

    result = sweep_score_thresholds(items)

    assert [row["threshold"] for row in result["thresholds"]] == [30, 40, 50, 60, 70, 80, 85, 90]
    assert result["thresholds"][0]["trade_count"] == 3
    assert result["best_threshold"] is not None


def test_sweep_score_thresholds_compares_trade_count_win_rate_and_expectancy():
    items = [_item(91, 2.0), _item(82, -1.0), _item(74, 0.5), _item(52, -1.0)]

    result = sweep_score_thresholds(items, thresholds=[50, 70, 80, 90])

    assert result["thresholds"] == [
        {"threshold": 50, "trade_count": 4, "wins": 2, "win_rate": 0.5, "average_realized_r": 0.12, "expectancy_r": 0.12},
        {"threshold": 70, "trade_count": 3, "wins": 2, "win_rate": 0.67, "average_realized_r": 0.5, "expectancy_r": 0.5},
        {"threshold": 80, "trade_count": 2, "wins": 1, "win_rate": 0.5, "average_realized_r": 0.5, "expectancy_r": 0.5},
        {"threshold": 90, "trade_count": 1, "wins": 1, "win_rate": 1.0, "average_realized_r": 2.0, "expectancy_r": 2.0},
    ]
    assert result["best_threshold"]["threshold"] == 90


def test_sweep_score_thresholds_respects_min_trades_for_best_threshold():
    items = [_item(91, 2.0), _item(82, -1.0), _item(74, 0.5), _item(52, -1.0)]

    result = sweep_score_thresholds(items, thresholds=[50, 70, 80, 90], min_trades=2)

    assert result["best_threshold"]["threshold"] == 70


def test_tune_thresholds_by_strategy_and_catalyst_segment():
    items = [
        _item(91, 2.0, strategy="gap_and_go", catalyst_type="earnings_beat"),
        _item(72, -1.0, strategy="gap_and_go", catalyst_type="earnings_beat"),
        _item(68, 1.0, strategy="vwap_hold", catalyst_type="insider_director_purchase"),
        _item(62, -0.5, strategy="vwap_hold", catalyst_type="insider_director_purchase"),
    ]

    result = tune_thresholds_by_segment(items, thresholds=[60, 70, 90], min_trades=1)

    assert result["gap_and_go|earnings_beat"]["best_threshold"]["threshold"] == 90
    assert result["vwap_hold|insider_director_purchase"]["best_threshold"]["threshold"] == 60
