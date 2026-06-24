"""Portfolio tracker — paper trade recommendations and track P&L.

Entry = last complete candle's close (yesterday).
Stop/target check only on candles AFTER entry.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from httpx import AsyncClient

from app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]
TRADES_FILE = REPO_ROOT / "runtime" / "ta-trades" / "trades.json"

STOP_ATR_MULTIPLE = 3.0       # was 2.0 — was too tight
TARGET1_RISK_MULTIPLE = 1.5
TARGET2_RISK_MULTIPLE = 2.6


def _load_trades():
    if TRADES_FILE.exists():
        return json.loads(TRADES_FILE.read_text())
    return {"trades": [], "next_id": 1}


def _save_trades(data):
    TRADES_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRADES_FILE.write_text(json.dumps(data, indent=2))


def _entry_stop_target(close, atr_pct):
    """Calculate entry, stop, targets. Returns None if invalid."""
    if not close or close <= 0:
        return None
    atr_dollars = close * atr_pct / 100
    stop_dist = atr_dollars * STOP_ATR_MULTIPLE
    if stop_dist <= 0:
        return None
    return {
        "entry": round(close, 2),
        "entry_zone": [round(close * 0.99, 2), round(close * 1.01, 2)],
        "stop_loss": round(close - stop_dist, 2),
        "target_1": round(close + stop_dist * TARGET1_RISK_MULTIPLE, 2),
        "target_2": round(close + stop_dist * TARGET2_RISK_MULTIPLE, 2),
        "risk_r": round(stop_dist / close * 100, 2),
    }


def add_trades_from_scan(scan_data, candles_map=None):
    """Add new open trades. Entry = last complete candle's close (not today's)."""
    trades_db = _load_trades()
    existing_tickers = {t["ticker"] for t in trades_db["trades"] if t["status"] == "open"}
    added = 0

    for rec in scan_data.get("top_recommendations", []):
        ticker = rec["ticker"]
        if ticker in existing_tickers:
            continue
        close = rec.get("close") or 0
        pl = _entry_stop_target(close, 3.0)
        if pl is None:
            continue

        # Entry timestamp: use yesterday's date if available
        entry_date = scan_data["scan_date"]

        trade = {
            "id": trades_db["next_id"] + added,
            "ticker": ticker,
            "score": rec["score"],
            "screens": rec["screens"],
            "sector": rec.get("sector", ""),
            "entry_date": entry_date,
            "status": "open",
            **pl,
        }
        trades_db["trades"].append(trade)
        added += 1

    trades_db["next_id"] += added
    _save_trades(trades_db)
    return added


async def update_open_trades():
    """Check open trades. Only checks candles AFTER entry date. No same-candle check."""
    trades_db = _load_trades()
    api_key = settings.massive_api_key
    if not api_key:
        return {"error": "no_api_key"}

    today = datetime.now(timezone.utc).date().isoformat()

    async with AsyncClient(base_url=settings.massive_base_url, timeout=30) as client:
        for trade in trades_db["trades"]:
            if trade["status"] != "open":
                continue
            try:
                resp = await client.get(
                    f"/v2/aggs/ticker/{trade['ticker']}/range/1/day/2026-06-01/{today}",
                    params={"adjusted": "true", "sort": "asc", "limit": 60, "apiKey": api_key},
                )
                if resp.status_code != 200 or not resp.json().get("results"):
                    continue
                raw = resp.json()["results"]

                # Convert Massive timestamps to date strings for comparison
                def _ts_date(ts_ms):
                    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).date().isoformat()

                # Find candles AFTER entry date (skip the entry-day candle)
                future_candles = []
                for r in raw:
                    if _ts_date(r["t"]) > trade["entry_date"]:
                        future_candles.append(r)

                if not future_candles:
                    continue  # no trading days after entry yet

                entry = trade["entry"]
                # Check all future candles: did high hit target? did low hit stop?
                hit_stop = any(c["l"] <= trade["stop_loss"] for c in future_candles)
                hit_t2 = any(c["h"] >= trade["target_2"] for c in future_candles)
                hit_t1 = any(c["h"] >= trade["target_1"] for c in future_candles)

                if hit_stop:
                    trade.update(status="loss", exit_price=trade["stop_loss"],
                                 exit_date=today, r_multiple=-1.0,
                                 pnl_pct=round((trade["stop_loss"] - entry) / entry * 100, 2))
                elif hit_t2:
                    trade.update(status="win", exit_price=trade["target_2"],
                                 exit_date=today, r_multiple=TARGET2_RISK_MULTIPLE,
                                 pnl_pct=round((trade["target_2"] - entry) / entry * 100, 2))
                elif hit_t1:
                    trade.update(status="win", exit_price=trade["target_1"],
                                 exit_date=today, r_multiple=TARGET1_RISK_MULTIPLE,
                                 pnl_pct=round((trade["target_1"] - entry) / entry * 100, 2))
                else:
                    trade["current_price"] = future_candles[-1]["c"]
                    trade["days_open"] = len(future_candles)
                    pnl = round((future_candles[-1]["c"] - entry) / entry * 100, 2)
                    trade["pnl_pct"] = pnl
            except Exception:
                continue

    _save_trades(trades_db)
    return _portfolio_summary(trades_db["trades"])


def timestamp_from_date(date_str):
    """Convert '2026-06-23' to a timestamp_ms for comparison."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp() * 1000)


def _portfolio_summary(trades):
    total = len(trades)
    open_trades = [t for t in trades if t["status"] == "open"]
    closed = [t for t in trades if t["status"] in ("win", "loss")]
    wins = [t for t in closed if t["status"] == "win"]
    losses = [t for t in closed if t["status"] == "loss"]
    win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0
    total_r = sum(t.get("r_multiple", 0) for t in closed)
    avg_r = round(total_r / len(closed), 2) if closed else 0
    return {
        "total_trades": total,
        "open": len(open_trades),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_r": round(total_r, 2),
        "avg_r": avg_r,
        "expectancy_r": round(avg_r * win_rate / 100, 2) if win_rate else 0,
    }
