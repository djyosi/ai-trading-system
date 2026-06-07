import pytest

from app.backtesting.batch import run_historical_batch


def _candle(index, close=10.0):
    return {"timestamp_ms": index * 86_400_000, "open": close, "high": close + 0.5, "low": close - 0.5, "close": close, "volume": 1_000_000}


class FakeProvider:
    def __init__(self):
        self.calls = []

    async def get_daily_candles(self, ticker, start, end):
        self.calls.append({"ticker": ticker, "start": start, "end": end})
        if ticker == "FAIL":
            raise RuntimeError("provider failed")
        return [_candle(i, close=10 + i * 0.2) for i in range(1, 8)]


@pytest.mark.asyncio
async def test_historical_batch_runs_walk_forward_for_many_tickers_and_summarizes():
    provider = FakeProvider()

    result = await run_historical_batch(
        tickers=["AAPL", "MSFT"],
        market_data_provider=provider,
        start="2025-01-01",
        end="2025-02-01",
        lookback_bars=3,
        horizon_bars=1,
    )

    assert [call["ticker"] for call in provider.calls] == ["AAPL", "MSFT"]
    assert result["tickers_total"] == 2
    assert result["tickers_completed"] == 2
    assert result["tickers_failed"] == 0
    assert result["evaluated_bars_total"] == 8
    assert set(result["results"]) == {"AAPL", "MSFT"}


@pytest.mark.asyncio
async def test_historical_batch_passes_catalyst_freshness_window_to_replay():
    class FakeProvider:
        async def get_daily_candles(self, ticker, start, end):
            return [_candle(i, close=10 + i) for i in range(1, 6)]

    result = await run_historical_batch(
        tickers=["AAPL"],
        market_data_provider=FakeProvider(),
        start="2025-01-01",
        end="2025-02-01",
        catalysts_by_ticker={"AAPL": [{"type": "earnings_beat", "timestamp_ms": 1 * 86_400_000}]},
        market_context={"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
        lookback_bars=3,
        horizon_bars=1,
        catalyst_max_age_minutes=60,
    )

    first = result["results"]["AAPL"]["items"][0]
    assert first["recommendation"]["inputs"]["catalyst"]["catalyst_type"] == "unknown"


@pytest.mark.asyncio
async def test_historical_batch_keeps_going_when_one_ticker_fails():
    provider = FakeProvider()

    result = await run_historical_batch(
        tickers=["AAPL", "FAIL", "MSFT"],
        market_data_provider=provider,
        start="2025-01-01",
        end="2025-02-01",
        lookback_bars=3,
        horizon_bars=1,
    )

    assert result["tickers_total"] == 3
    assert result["tickers_completed"] == 2
    assert result["tickers_failed"] == 1
    assert result["errors"] == {"FAIL": "provider failed"}
    assert set(result["results"]) == {"AAPL", "MSFT"}
