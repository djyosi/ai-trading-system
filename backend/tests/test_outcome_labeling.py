from app.backtesting.outcomes import label_recommendation_outcome


def _recommendation():
    return {
        "ticker": "PAX",
        "status": "active_watch",
        "direction": "long",
        "entry_zone": [11.43, 11.67],
        "stop_loss": 11.09,
        "targets": [12.24, 12.75],
        "risk_reward": 1.5,
    }


def test_labels_target_hit_before_stop_for_long_recommendation():
    outcome = label_recommendation_outcome(
        _recommendation(),
        future_candles=[
            {"timestamp_ms": 1, "high": 11.80, "low": 11.35, "close": 11.70},
            {"timestamp_ms": 2, "high": 12.30, "low": 11.65, "close": 12.20},
            {"timestamp_ms": 3, "high": 12.80, "low": 12.10, "close": 12.60},
        ],
    )

    assert outcome["status"] == "closed"
    assert outcome["target_hit"] is True
    assert outcome["stop_hit"] is False
    assert outcome["bars_to_target"] == 2
    assert outcome["realized_r"] == 1.5
    assert outcome["max_favorable_excursion_r"] == 2.72
    assert outcome["max_adverse_excursion_r"] == -0.43


def test_labels_stop_hit_before_target_for_long_recommendation():
    outcome = label_recommendation_outcome(
        _recommendation(),
        future_candles=[
            {"timestamp_ms": 1, "high": 11.90, "low": 11.20, "close": 11.60},
            {"timestamp_ms": 2, "high": 11.70, "low": 11.00, "close": 11.05},
            {"timestamp_ms": 3, "high": 12.40, "low": 11.80, "close": 12.20},
        ],
    )

    assert outcome["status"] == "closed"
    assert outcome["target_hit"] is False
    assert outcome["stop_hit"] is True
    assert outcome["bars_to_stop"] == 2
    assert outcome["realized_r"] == -1.0


def test_labels_open_outcome_when_neither_target_nor_stop_hit():
    outcome = label_recommendation_outcome(
        _recommendation(),
        future_candles=[
            {"timestamp_ms": 1, "high": 11.95, "low": 11.30, "close": 11.60},
            {"timestamp_ms": 2, "high": 12.00, "low": 11.40, "close": 11.80},
        ],
    )

    assert outcome["status"] == "open"
    assert outcome["target_hit"] is False
    assert outcome["stop_hit"] is False
    assert outcome["realized_r"] is None


def test_no_trade_recommendation_is_skipped_not_scored():
    recommendation = _recommendation()
    recommendation["status"] = "no_trade"

    outcome = label_recommendation_outcome(recommendation, future_candles=[])

    assert outcome == {
        "status": "skipped",
        "target_hit": False,
        "stop_hit": False,
        "realized_r": None,
        "skip_reason": "recommendation_was_no_trade",
    }


def test_outcome_labeling_uses_only_future_candles_after_recommendation_time():
    outcome = label_recommendation_outcome(
        _recommendation(),
        future_candles=[
            {"timestamp_ms": 50, "high": 13.00, "low": 10.80, "close": 12.90},
            {"timestamp_ms": 101, "high": 11.90, "low": 11.30, "close": 11.70},
            {"timestamp_ms": 102, "high": 12.30, "low": 11.60, "close": 12.20},
        ],
        recommendation_timestamp_ms=100,
    )

    assert outcome["target_hit"] is True
    assert outcome["stop_hit"] is False
    assert outcome["bars_to_target"] == 2
