from fastapi.testclient import TestClient

from app.api.routes.backtests import get_backtest_market_data_provider
from app.main import app


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


def test_paper_validation_research_api_runs_broad_paper_safe_summary():
    provider = FakeResearchProvider()
    app.dependency_overrides[get_backtest_market_data_provider] = lambda: provider
    client = TestClient(app)

    try:
        response = client.post(
            "/api/backtests/paper-validation-research",
            json={
                "start": "2026-01-01",
                "end": "2026-02-01",
                "lookback_bars": 3,
                "horizon_bars": 1,
                "actionable_score_threshold": 20,
                "thresholds": [20, 40, 60],
                "min_trades": 1,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_type"] == "phase_3_paper_validation_research"
    assert payload["universe_preset"] == "liquid_research_100"
    assert payload["orders_enabled"] is False
    assert payload["tickers_total"] == 100
    assert provider.candle_calls[0] == {"ticker": "AAPL", "start": "2026-01-01", "end": "2026-02-01"}
    assert provider.candle_calls[-1] == {"ticker": "ABNB", "start": "2026-01-01", "end": "2026-02-01"}
    assert payload["paper_validation"]["mode"] == "paper_simulation"
    assert payload["paper_validation"]["orders_enabled"] is False
    assert "items" not in payload["paper_validation"]
    assert "results" not in payload
    assert "phase_3_readiness" in payload["research_report"]
