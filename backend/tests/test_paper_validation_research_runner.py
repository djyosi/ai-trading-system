import pytest

from app.backtesting.paper_validation_research import run_paper_validation_research


def _candle(index, high, low, close, volume=5_000_000):
    return {
        "timestamp_ms": index * 86_400_000,
        "open": close - 0.2,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "vwap": round((high + low + close) / 3, 2),
    }


class FakeResearchProvider:
    def __init__(self):
        self.candle_calls = []

    async def get_daily_candles(self, ticker, start, end):
        self.candle_calls.append({"ticker": ticker, "start": start, "end": end})
        return [
            _candle(1, 210.0, 209.0, 210.0),
            _candle(2, 211.0, 210.0, 211.0),
            _candle(3, 212.0, 211.0, 212.0),
            _candle(4, 214.0, 212.0, 213.5, volume=7_000_000),
            _candle(5, 216.0, 213.0, 215.0, volume=8_000_000),
        ]


@pytest.mark.asyncio
async def test_paper_validation_research_runner_defaults_to_broad_paper_safe_summary():
    provider = FakeResearchProvider()

    result = await run_paper_validation_research(
        market_data_provider=provider,
        start="2026-01-01",
        end="2026-02-01",
        lookback_bars=3,
        horizon_bars=1,
        actionable_score_threshold=20,
        thresholds=[20, 40, 60],
        min_trades=1,
    )

    assert result["run_type"] == "phase_3_paper_validation_research"
    assert result["universe_preset"] == "liquid_research_100"
    assert result["orders_enabled"] is False
    assert result["tickers_total"] == 100
    assert result["tickers_completed"] == 100
    assert provider.candle_calls[0] == {"ticker": "AAPL", "start": "2026-01-01", "end": "2026-02-01"}
    assert provider.candle_calls[-1] == {"ticker": "ABNB", "start": "2026-01-01", "end": "2026-02-01"}
    assert len({call["ticker"] for call in provider.candle_calls}) == 100
    assert result["run_configuration"] == {
        "data_source": "provider_history",
        "universe_preset": "liquid_research_100",
        "tickers_requested": 100,
        "start": "2026-01-01",
        "end": "2026-02-01",
        "include_news_catalysts": False,
        "include_market_context": False,
        "market_context_source": "none",
        "lookback_bars": 3,
        "horizon_bars": 1,
        "catalyst_max_age_minutes": None,
        "actionable_score_threshold": 20,
        "thresholds": [20, 40, 60],
        "min_trades": 1,
        "paper_account_equity": 100_000,
        "paper_risk_fraction": 0.01,
        "orders_enabled": False,
    }
    assert result["paper_validation"]["mode"] == "paper_simulation"
    assert result["paper_validation"]["orders_enabled"] is False
    assert result["paper_validation"]["data_source"] == "historical_backtest"
    assert result["paper_validation"]["summary"]["recommendations_total"] > 0
    assert "items" not in result["paper_validation"]
    assert "results" not in result
    assert result["research_report"]["phase_3_readiness"]["status"] in {
        "paper_validation_started",
        "needs_paper_validation_sample",
    }
    assert result["aggregate_threshold_sweep"]["min_trades"] == 1
