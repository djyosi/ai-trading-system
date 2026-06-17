from fastapi import APIRouter, Query
from pathlib import Path
import json

from app.ta_screener.scanner import run_screen, SCREENS
from app.ta_screener.daily_run import run_daily_scan

router = APIRouter(prefix="/api/screener/ta", tags=["ta-screener"])

REPO_ROOT = Path(__file__).resolve().parents[4]
SCANS_DIR = REPO_ROOT / "runtime" / "ta-scans"


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


@router.get("/scan")
async def run_full_scan():
    """Run full daily scan on all tickers and return top recommendations."""
    result = await run_daily_scan()
    return result


async def run_daily_and_return():
    """Run full daily scan and return results."""
    result = await run_daily_scan()
    return result


@router.get("/screens")
async def list_screens():
    """List all available screens."""
    return {
        name: {"name": s["name"], "description": s["description"]}
        for name, s in SCREENS.items()
    }


@router.get("/latest")
async def latest_scan():
    """Get the latest saved scan results."""
    scans = sorted(SCANS_DIR.glob("scan-*.json")) if SCANS_DIR.exists() else []
    if not scans:
        return {"status": "no_scans_yet", "message": "Run /api/screener/ta/scan to generate"}
    latest = json.loads(scans[-1].read_text())
    return latest


@router.get("/top")
async def top_recommendations(limit: int = 10):
    """Get top N recommendations from latest scan."""
    scans = sorted(SCANS_DIR.glob("scan-*.json")) if SCANS_DIR.exists() else []
    if not scans:
        return {"recommendations": [], "message": "No scans available"}
    latest = json.loads(scans[-1].read_text())
    return {"recommendations": latest.get("top_recommendations", [])[:limit]}
