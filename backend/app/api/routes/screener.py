from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from httpx import AsyncClient

from app.core.config import settings
from app.features.sectors import get_sector
from app.technicals.entry_signals import analyze_technical

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("/ta")
async def ta_screener(
    tickers: str = Query("", description="Comma-separated tickers"),
    min_score: int = Query(0, description="Minimum absolute score to include"),
    signal: str = Query("", description="Filter: buy, sell, strong_buy, strong_sell"),
    limit: int = Query(50, description="Max results"),
):
    """Screen tickers by current technical analysis signals."""
    if not tickers:
        return {"tickers": [], "signal_filter": signal, "count": 0}

    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    results = []
    api_key = settings.massive_api_key

    if not api_key:
        return {"tickers": [], "error": "api_key_not_configured", "count": 0}

    async with AsyncClient(base_url=settings.massive_base_url, timeout=30) as client:
        for ticker in ticker_list[:limit]:
            try:
                end = datetime.now(timezone.utc).date()
                start = end - timedelta(days=90)
                resp = await client.get(
                    f"/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}",
                    params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
                )
                if resp.status_code != 200:
                    continue
                payload = resp.json()
                raw = payload.get("results", [])
                if len(raw) < 10:
                    continue

                candles = [{"timestamp_ms": r["t"], "open": r["o"], "high": r["h"], "low": r["l"], "close": r["c"], "volume": r["v"]} for r in raw]
                analysis = analyze_technical(ticker, candles)
                sig = analysis["signal"]

                if signal and signal not in sig:
                    continue
                if abs(analysis["score"]) < min_score:
                    continue

                results.append({
                    "ticker": ticker,
                    "sector": get_sector(ticker),
                    "signal": sig,
                    "score": analysis["score"],
                    "price": analysis.get("current_price"),
                    "channel": analysis.get("channel", {}).get("type"),
                    "volume": analysis.get("volume_trend"),
                    "divergence": analysis.get("volume_divergence"),
                    "pattern": analysis.get("candle_pattern", {}).get("pattern"),
                    "reasons": analysis["reasons"],
                })
            except Exception:
                continue

    return {"tickers": results, "signal_filter": signal, "count": len(results)}
