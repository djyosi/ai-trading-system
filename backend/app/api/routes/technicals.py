from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from httpx import AsyncClient

from app.core.config import settings
from app.technicals.entry_signals import analyze_technical

router = APIRouter(prefix="/api/technicals", tags=["technicals"])


@router.get("/{ticker}")
async def technical_analysis(ticker: str):
    """Run full technical analysis on a single ticker using live Massive data."""
    ticker = ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    async with AsyncClient(base_url=settings.massive_base_url, timeout=30) as client:
        api_key = settings.massive_api_key
        if not api_key:
            return {
                "ticker": ticker,
                "signal": "hold",
                "reasons": ["api_key_not_configured"],
                "orders_enabled": False,
                "data_source": "none",
            }

        try:
            # Fetch daily candles (last 60 days)
            end = datetime.now(timezone.utc).date()
            start = end - timedelta(days=90)
            response = await client.get(
                f"/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}",
                params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])

            if not results:
                return {
                    "ticker": ticker,
                    "signal": "hold",
                    "reasons": ["no_candle_data"],
                    "orders_enabled": False,
                    "data_source": "massive",
                }

            candles = [
                {
                    "timestamp_ms": r.get("t"),
                    "open": r.get("o"),
                    "high": r.get("h"),
                    "low": r.get("l"),
                    "close": r.get("c"),
                    "volume": r.get("v"),
                }
                for r in results
            ]

            analysis = analyze_technical(ticker, candles)

            return {
                **analysis,
                "orders_enabled": False,
                "data_source": "massive",
                "candle_count": len(candles),
                "candle_range": f"{start}..{end}",
            }

        except Exception as exc:
            return {
                "ticker": ticker,
                "signal": "hold",
                "reasons": [f"provider_error: {str(exc)[:100]}"],
                "orders_enabled": False,
                "data_source": "massive",
            }
