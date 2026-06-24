"""Convenience wrapper: fetch candles using the fallback provider chain.

Usage:
    from app.providers.fetch import fetch_candles
    candles = await fetch_candles("AAPL", "2026-01-01", "2026-06-24")
"""

from app.providers import get_provider


async def fetch_candles(ticker, start, end):
    """Fetch daily candles for a ticker. Tries Massive → Yahoo → Cache.

    Returns list of {timestamp_ms, open, high, low, close, volume} or None.
    """
    provider = get_provider()
    return await provider.get_daily_candles(ticker, start, end)


async def fetch_many(tickers, start, end, batch=50):
    """Fetch candles for many tickers. Returns dict of {ticker: candles}."""
    provider = get_provider()
    return await provider.get_many(tickers, start, end, batch=batch)
