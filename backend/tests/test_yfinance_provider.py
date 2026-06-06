from datetime import datetime, timezone

import pandas as pd
import pytest

from app.providers.yfinance_provider import YFinanceProvider


class FakeTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, start=None, end=None, interval="1d", auto_adjust=False, prepost=True):
        index = pd.DatetimeIndex([datetime(2024, 6, 3, 13, 30, tzinfo=timezone.utc)])
        return pd.DataFrame(
            {
                "Open": [100.0],
                "High": [105.0],
                "Low": [99.0],
                "Close": [104.0],
                "Volume": [1234567],
            },
            index=index,
        )


class EmptyTicker:
    def history(self, start=None, end=None, interval="1d", auto_adjust=False, prepost=True):
        return pd.DataFrame()


@pytest.mark.asyncio
async def test_yfinance_daily_candles_are_normalized():
    provider = YFinanceProvider(ticker_factory=FakeTicker)

    candles = await provider.get_daily_candles(
        "AAPL",
        datetime(2024, 6, 1, tzinfo=timezone.utc),
        datetime(2024, 6, 4, tzinfo=timezone.utc),
    )

    assert candles == [
        {
            "ticker": "AAPL",
            "provider": "yfinance",
            "timeframe": "1d",
            "timestamp": "2024-06-03T13:30:00+00:00",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 104.0,
            "volume": 1234567,
            "vwap": None,
            "transactions": None,
            "raw": {
                "Open": 100.0,
                "High": 105.0,
                "Low": 99.0,
                "Close": 104.0,
                "Volume": 1234567,
            },
        }
    ]


@pytest.mark.asyncio
async def test_yfinance_intraday_candles_use_requested_interval():
    captured = {}

    class CapturingTicker(FakeTicker):
        def history(self, start=None, end=None, interval="1d", auto_adjust=False, prepost=True):
            captured["interval"] = interval
            captured["prepost"] = prepost
            return super().history(start=start, end=end, interval=interval, auto_adjust=auto_adjust, prepost=prepost)

    provider = YFinanceProvider(ticker_factory=CapturingTicker)

    candles = await provider.get_intraday_candles(
        "MSFT",
        datetime(2024, 6, 1, tzinfo=timezone.utc),
        datetime(2024, 6, 4, tzinfo=timezone.utc),
        timeframe="5m",
    )

    assert captured == {"interval": "5m", "prepost": True}
    assert candles[0]["timeframe"] == "5m"
    assert candles[0]["ticker"] == "MSFT"


@pytest.mark.asyncio
async def test_yfinance_empty_history_returns_empty_list():
    provider = YFinanceProvider(ticker_factory=lambda ticker: EmptyTicker())

    candles = await provider.get_daily_candles(
        "AAPL",
        datetime(2024, 6, 1, tzinfo=timezone.utc),
        datetime(2024, 6, 4, tzinfo=timezone.utc),
    )

    assert candles == []


@pytest.mark.asyncio
async def test_yfinance_snapshot_returns_none_because_provider_is_historical_fallback():
    provider = YFinanceProvider(ticker_factory=FakeTicker)

    assert await provider.get_snapshot("AAPL") is None
