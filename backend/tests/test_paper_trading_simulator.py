from app.paper_trading.simulator import simulate_paper_trade


def _recommendation():
    return {
        "ticker": "AAPL",
        "direction": "long",
        "status": "active_watch",
        "entry_zone": [10.0, 10.2],
        "stop_loss": 9.5,
        "targets": [11.0, 12.0],
    }


def _candle(index, high, low, close):
    return {"timestamp_ms": index, "high": high, "low": low, "close": close}


def test_paper_trade_simulation_enters_on_zone_and_exits_at_first_target():
    result = simulate_paper_trade(
        _recommendation(),
        candles=[_candle(1, 10.1, 9.9, 10.05), _candle(2, 11.2, 10.2, 11.0)],
        account_equity=100_000,
        risk_fraction=0.01,
    )

    assert result == {
        "status": "closed",
        "ticker": "AAPL",
        "entry_price": 10.1,
        "exit_price": 11.0,
        "exit_reason": "target_hit",
        "shares": 1666,
        "risk_amount": 1000.0,
        "realized_pnl": 1499.4,
        "realized_r": 1.5,
    }


def test_paper_trade_simulation_skips_no_trade_recommendations():
    recommendation = _recommendation()
    recommendation["status"] = "no_trade"

    result = simulate_paper_trade(recommendation, candles=[_candle(1, 10.1, 9.9, 10.0)])

    assert result["status"] == "skipped"
    assert result["exit_reason"] == "no_trade_recommendation"


def test_paper_trade_simulation_skips_short_watch_until_short_model_exists():
    recommendation = _recommendation()
    recommendation["direction"] = "short_watch"

    result = simulate_paper_trade(recommendation, candles=[_candle(1, 10.1, 9.9, 10.0)])

    assert result == {
        "status": "skipped",
        "ticker": "AAPL",
        "exit_reason": "short_model_not_implemented",
    }


def test_paper_trade_simulation_reports_not_triggered_when_entry_zone_never_trades():
    result = simulate_paper_trade(_recommendation(), candles=[_candle(1, 9.8, 9.2, 9.4)])

    assert result["status"] == "not_triggered"
    assert result["exit_reason"] == "entry_not_hit"
