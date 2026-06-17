from fastapi import APIRouter, Query
from app.ta_screener.scanner import run_screen, SCREENS

router = APIRouter(prefix="/api/screener/ta", tags=["ta-screener"])


@router.get("/run")
async def ta_screen_run(
    screen: str = Query("bollinger_bounce"),
    tickers: str = Query("", description="Comma-separated tickers"),
):
    """Run a technical screen on tickers."""
    if not tickers:
        return {"screen": screen, "matches": [], "count": 0}
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    result = await run_screen(ticker_list, screen)
    return result


@router.get("/screens")
async def list_screens():
    """List all available screens."""
    return {
        name: {"name": s["name"], "description": s["description"]}
        for name, s in SCREENS.items()
    }
