"""Data provider abstraction with fallback chain.

Usage:
    from app.providers import get_provider
    provider = get_provider()  # returns FallbackProvider
    candles = await provider.get_daily_candles("AAPL", "2026-01-01", "2026-06-24")
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import json

CACHE_DIR = Path(__file__).resolve().parents[2] / "runtime" / "provider-cache"

# ── Abstract ──────────────────────────────────────────────────────

class DataProvider(ABC):
    @abstractmethod
    async def get_daily_candles(self, ticker, start, end):
        """Return list of {timestamp_ms, open, high, low, close, volume}."""
        ...

# ── Massive (Polygon.io) ──────────────────────────────────────────

class MassiveProvider(DataProvider):
    def __init__(self, api_key, base_url="https://api.polygon.io"):
        self.api_key = api_key
        self.base_url = base_url

    async def get_daily_candles(self, ticker, start, end):
        from httpx import AsyncClient
        async with AsyncClient(base_url=self.base_url, timeout=30) as c:
            resp = await c.get(
                f"/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}",
                params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": self.api_key},
            )
            if resp.status_code != 200:
                return None
            raw = resp.json().get("results", [])
            if not raw:
                return None
            return [{
                "timestamp_ms": r["t"],
                "open": r["o"],
                "high": r["h"],
                "low": r["l"],
                "close": r["c"],
                "volume": r["v"],
            } for r in raw]

# ── Yahoo Finance ─────────────────────────────────────────────────

class YahooFinanceProvider(DataProvider):
    """Fallback using yfinance (free, no API key). Requires yfinance installed."""

    async def get_daily_candles(self, ticker, start, end):
        try:
            import yfinance as yf
            import pandas as pd
            stock = yf.Ticker(ticker)
            df = stock.history(start=start, end=end)
            if df.empty:
                return None
            result = []
            for idx, row in df.iterrows():
                result.append({
                    "timestamp_ms": int(idx.timestamp() * 1000),
                    "open": row["Open"],
                    "high": row["High"],
                    "low": row["Low"],
                    "close": row["Close"],
                    "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
                })
            return result
        except Exception:
            return None

# ── Local Cache ───────────────────────────────────────────────────

class CachedProvider(DataProvider):
    """Read previously fetched candle data from local JSON cache."""

    async def get_daily_candles(self, ticker, start, end):
        cache_path = CACHE_DIR / f"{ticker}.json"
        if not cache_path.exists():
            return None
        try:
            data = json.loads(cache_path.read_text())
            # Filter by date range
            start_ms = int(datetime.strptime(start, "%Y-%m-%d").timestamp() * 1000) if isinstance(start, str) else 0
            end_ms = int(datetime.strptime(end, "%Y-%m-%d").timestamp() * 1000) if isinstance(end, str) else 9999999999999
            return [c for c in data if start_ms <= c["timestamp_ms"] <= end_ms]
        except Exception:
            return None

# ── Fallback Chain ────────────────────────────────────────────────

class FallbackProvider(DataProvider):
    """Tries Massive → Yahoo → Cache, returns first success."""

    def __init__(self, massive_api_key):
        self.providers = [
            MassiveProvider(massive_api_key),
            YahooFinanceProvider(),
            CachedProvider(),
        ]

    async def get_daily_candles(self, ticker, start, end):
        errors = []
        for provider in self.providers:
            try:
                result = await provider.get_daily_candles(ticker, start, end)
                if result is not None and len(result) > 0:
                    return result
            except Exception as e:
                errors.append(f"{provider.__class__.__name__}: {e}")
        return None

    async def get_many(self, tickers, start, end, batch=50):
        """Fetch candles for many tickers, returns dict of {ticker: candles}."""
        import asyncio

        results = {}
        for i in range(0, len(tickers), batch):
            batch_list = tickers[i:i+batch]

            async def fetch_one(t):
                try:
                    candles = await self.get_daily_candles(t, start, end)
                    if candles:
                        results[t] = candles
                except Exception:
                    pass

            await asyncio.gather(*[fetch_one(t) for t in batch_list])
        return results

# ── Factory ───────────────────────────────────────────────────────

_fallback = None

def get_provider():
    """Return singleton FallbackProvider."""
    global _fallback
    if _fallback is None:
        from app.core.config import settings
        _fallback = FallbackProvider(settings.massive_api_key or "")
    return _fallback
