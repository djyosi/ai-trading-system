"""Standalone screener runner: fetches data from Massive, runs screens, returns results."""

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.core.config import settings
from app.ta_screener import SCREENS
from app.ta_screener.indicators import compute_indicators, check_screen


async def run_screen(tickers, screen_name, limit=500):
    """Run a single screen on a list of tickers. Returns matched tickers."""
    screen = SCREENS.get(screen_name)
    if not screen:
        raise ValueError(f"Unknown screen: {screen_name}. Available: {list(SCREENS.keys())}")

    results = []
    api_key = settings.massive_api_key
    if not api_key:
        return {"screen": screen_name, "matches": [], "error": "no_api_key"}

    async with AsyncClient(base_url=settings.massive_base_url, timeout=30) as client:
        for ticker in tickers[:limit]:
            try:
                end = datetime.now(timezone.utc).date()
                start = end - timedelta(days=365)  # need up to 200+ candles for SMA 200

                resp = await client.get(
                    f"/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}",
                    params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
                )
                if resp.status_code != 200:
                    continue

                payload = resp.json()
                raw = payload.get("results", [])
                if len(raw) < screen.get("min_candles", 20):
                    continue

                candles = [{"timestamp_ms": r["t"], "open": r["o"], "high": r["h"],
                            "low": r["l"], "close": r["c"], "volume": r["v"]} for r in raw]

                indicators = compute_indicators(candles)
                if check_screen(indicators, screen_name):
                    results.append({
                        "ticker": ticker,
                        "close": indicators.get("close"),
                        "rsi": indicators.get("rsi_14"),
                        "volume_ratio": round(indicators.get("volume", 0) / (indicators.get("avg_volume_20") or 1), 1),
                    })
            except Exception:
                continue

    return {"screen": screen_name, "description": screen["description"], "matches": results, "count": len(results)}


async def run_all_screens(tickers, limit=500):
    """Run all defined screens and return combined results."""
    results = {}
    for name in SCREENS:
        results[name] = await run_screen(tickers, name, limit)
    return results
