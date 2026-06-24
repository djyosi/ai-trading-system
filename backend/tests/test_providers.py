"""Test data provider abstraction and fallback chain."""

import pytest
from app.providers import (
    YahooFinanceProvider, FallbackProvider, get_provider,
)


@pytest.mark.asyncio
async def test_yahoo_provider_returns_candles():
    """Yahoo fallback should return valid candle data for liquid tickers."""
    provider = YahooFinanceProvider()
    candles = await provider.get_daily_candles("AAPL", "2026-06-01", "2026-06-24")
    assert candles is not None
    assert len(candles) > 0
    assert "timestamp_ms" in candles[0]
    assert candles[0]["close"] > 0


@pytest.mark.asyncio
async def test_fallback_chain_returns_candles():
    """FallbackProvider should return data even without API key (Yahoo fallback)."""
    provider = FallbackProvider(massive_api_key="")
    candles = await provider.get_daily_candles("MSFT", "2026-06-01", "2026-06-24")
    assert candles is not None
    assert len(candles) > 0
    assert candles[0]["close"] > 0


def test_get_provider_returns_singleton():
    """Factory returns the same instance each time."""
    p1 = get_provider()
    p2 = get_provider()
    assert p1 is p2
