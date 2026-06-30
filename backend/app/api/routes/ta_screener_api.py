from fastapi import APIRouter, Query
from pathlib import Path
import json

from app.ta_screener.scanner import run_screen, SCREENS
from app.ta_screener.daily_run import run_daily_scan
from app.ta_screener.paper_trade import track_outcomes
from app.ta_screener.portfolio import update_open_trades

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


@router.get("/outcomes")
async def paper_outcomes():
    """Track how yesterday's top recommendations performed today."""
    result = await track_outcomes()
    return result


@router.get("/portfolio")
async def portfolio(date: str = None):
    """Get portfolio summary + all trades. Optional date parameter."""
    from app.ta_screener.portfolio import _portfolio_summary, _load_trades

    if date:
        # Load historical scan data for that date
        scan_path = SCANS_DIR / f"scan-{date}.json"
        if scan_path.exists():
            scan_data = json.loads(scan_path.read_text())
            return {
                "scan_date": date,
                "historical": True,
                "top_recommendations": scan_data.get("top_recommendations", [])[:10],
                "summary": {
                    "total_trades": 0, "open": 0, "closed": 0,
                    "wins": 0, "losses": 0,
                },
            }
        return {"error": "no_data", "scan_date": date}

    trades_db = _load_trades()
    summary = _portfolio_summary(trades_db["trades"])
    return {"summary": summary, "trades": trades_db["trades"]}


@router.get("/scans")
async def scan_dates():
    """Get list of available scan dates."""
    files = sorted(SCANS_DIR.glob("scan-*.json"))
    dates = [f.stem.replace("scan-", "") for f in files]
    return {"dates": dates}


@router.post("/portfolio/update")
async def update_portfolio():
    """Check open trades and close winners/losers."""
    summary = await update_open_trades()
    return summary


@router.get("/top")
async def top_recommendations(limit: int = 10):
    """Get top N recommendations from latest scan."""
    scans = sorted(SCANS_DIR.glob("scan-*.json")) if SCANS_DIR.exists() else []
    if not scans:
        return {"recommendations": [], "message": "No scans available"}
    latest = json.loads(scans[-1].read_text())
    return {"recommendations": latest.get("top_recommendations", [])[:limit]}


@router.get("/ibkr-status")
def ibkr_status(position_size: int = 10000, limit: int = 10):
    """Show real IBKR paper positions and planned orders from latest TA scan.

    Read-only endpoint: it does not place orders. It shows what IBKR currently
    holds and what the execution script would buy next, skipping already-held
    tickers.
    """
    scans = sorted(SCANS_DIR.glob("scan-*.json")) if SCANS_DIR.exists() else []
    latest = json.loads(scans[-1].read_text()) if scans else {"top_recommendations": [], "scan_date": None}
    top = latest.get("top_recommendations", [])[:limit]

    try:
        import asyncio

        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        from app.ibkr.bridge import IBKRBridge

        bridge = IBKRBridge()
        if not bridge.connect():
            return {
                "status": "offline",
                "message": "TWS paper is not connected/running on port 7497",
                "scan_date": latest.get("scan_date"),
                "positions": [],
                "planned_orders": _planned_orders(top, set(), position_size),
            }
        try:
            account = bridge.get_account_summary()
            positions = bridge.get_positions()
        finally:
            bridge.disconnect()
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "scan_date": latest.get("scan_date"),
            "positions": [],
            "planned_orders": _planned_orders(top, set(), position_size),
        }

    held = {p["ticker"] for p in positions}
    return {
        "status": "connected",
        "scan_date": latest.get("scan_date"),
        "account": account,
        "positions": positions,
        "planned_orders": _planned_orders(top, held, position_size),
    }


def _planned_orders(recommendations, held_tickers, position_size):
    planned = []
    for rec in recommendations:
        ticker = rec.get("ticker")
        price = rec.get("close") or 0
        if ticker in held_tickers:
            planned.append({
                "ticker": ticker,
                "action": "skip",
                "reason": "already_held",
                "score": rec.get("score"),
                "price": price,
            })
            continue
        if not price or price <= 0:
            planned.append({
                "ticker": ticker,
                "action": "skip",
                "reason": "no_price",
                "score": rec.get("score"),
                "price": price,
            })
            continue
        qty = max(1, int(position_size / price))
        planned.append({
            "ticker": ticker,
            "action": "BUY",
            "quantity": qty,
            "estimated_cost": round(qty * price, 2),
            "price": price,
            "score": rec.get("score"),
            "reason": "top_ta_pick_not_held",
        })
    return planned
