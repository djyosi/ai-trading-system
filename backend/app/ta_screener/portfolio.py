"""Portfolio tracker with trailing stop, partial close, and time stop.

Entry = last complete candle's close (yesterday).
Stop/target check only on candles AFTER entry.

Trailing stop rules:
  +5%  → stop moves to breakeven (entry)
  +10% → stop trails by 5% of highest
  +15% → stop trails by 7% of highest

Partial close at target 1 (+13.5%): sell 50%, trail rest to target 2.
Time stop: close if no progress (>2%) within 10 days.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from httpx import AsyncClient

from app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]
TRADES_FILE = REPO_ROOT / "runtime" / "ta-trades" / "trades.json"

STOP_ATR_MULTIPLE = 3.0
TARGET1_RISK_MULTIPLE = 1.5
TARGET2_RISK_MULTIPLE = 2.6

# Trailing stop thresholds
BREAKEVEN_TRIGGER = 0.05      # +5% → stop to entry
TRAIL1_TRIGGER = 0.10         # +10% → trail 5%
TRAIL1_DISTANCE = 0.05
TRAIL2_TRIGGER = 0.15         # +15% → trail 7%
TRAIL2_DISTANCE = 0.07

# Time stop
MAX_DAYS_NO_PROGRESS = 10     # close if flat >10 days
MIN_PROGRESS_PCT = 2.0


def _load_trades():
    if TRADES_FILE.exists():
        return json.loads(TRADES_FILE.read_text())
    return {"trades": [], "next_id": 1}


def _save_trades(data):
    TRADES_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRADES_FILE.write_text(json.dumps(data, indent=2))


def _entry_stop_target(close, atr_pct):
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
        "highest_price": round(close, 2),   # track highest seen
        "partial_closed": False,             # sold 50% at target 1?
    }


def add_trades_from_scan(scan_data):
    trades_db = _load_trades()
    existing_tickers = {t["ticker"] for t in trades_db["trades"] if t["status"] == "open"}
    added = 0

    from datetime import datetime, timedelta
    entry_date_obj = datetime.strptime(scan_data["scan_date"], "%Y-%m-%d") - timedelta(days=1)
    entry_date = entry_date_obj.strftime("%Y-%m-%d")

    for rec in scan_data.get("top_recommendations", []):
        ticker = rec["ticker"]
        if ticker in existing_tickers:
            continue
        close = rec.get("close") or 0
        pl = _entry_stop_target(close, 3.0)
        if pl is None:
            continue
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
    """Update all open trades. Apply trailing stop, partial close, time stop."""
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

                def _ts_date(ts_ms):
                    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).date().isoformat()

                # Only look at candles AFTER entry date
                future = [r for r in raw if _ts_date(r["t"]) > trade["entry_date"]]
                if not future:
                    continue

                entry = trade["entry"]
                stop = trade["stop_loss"]
                t1 = trade["target_1"]
                t2 = trade["target_2"]
                highest = trade.get("highest_price", entry)
                partial = trade.get("partial_closed", False)
                days_open = len(future)

                # Scan all future candles
                for c in future:
                    close = c["c"]
                    high = c["h"]
                    low = c["l"]

                    # Track highest close
                    if close > highest:
                        highest = close

                    # ── CHECK STOP ──
                    if low <= stop:
                        trade.update(status="loss", exit_price=round(stop, 2),
                                     exit_date=today, r_multiple=-1.0,
                                     pnl_pct=round((stop - entry) / entry * 100, 2))
                        break

                    # ── CHECK TARGET 2 (full close) ──
                    if high >= t2:
                        trade.update(status="win", exit_price=round(t2, 2),
                                     exit_date=today, r_multiple=TARGET2_RISK_MULTIPLE,
                                     pnl_pct=round((t2 - entry) / entry * 100, 2))
                        break

                    # ── CHECK TARGET 1 (partial close 50%) ──
                    if high >= t1 and not partial:
                        partial = True
                        trade["partial_closed"] = True
                        trade["partial_price"] = round(t1, 2)
                        trade["partial_pnl"] = round((t1 - entry) / entry * 100, 2)
                        trade["partial_date"] = today
                        # Raise stop of remaining position to breakeven + 1%
                        new_stop = round(entry * 1.01, 2)
                        if new_stop > stop:
                            stop = new_stop
                            trade["stop_loss"] = stop
                        continue  # keep checking rest of candles for stop/t2

                # If still open after checking all candles, apply trailing stop
                if trade["status"] == "open":
                    gain = (highest / entry) - 1
                    old_stop = trade["stop_loss"]

                    # ── TRAILING STOP LOGIC ──
                    # +15%+ → trail 7%
                    if gain >= TRAIL2_TRIGGER:
                        new_stop = round(highest * (1 - TRAIL2_DISTANCE), 2)
                        if new_stop > old_stop:
                            trade["stop_loss"] = new_stop
                    # +10%+ → trail 5%
                    elif gain >= TRAIL1_TRIGGER:
                        new_stop = round(highest * (1 - TRAIL1_DISTANCE), 2)
                        if new_stop > old_stop:
                            trade["stop_loss"] = new_stop
                    # +5%+ → breakeven
                    elif gain >= BREAKEVEN_TRIGGER:
                        if old_stop < entry:
                            trade["stop_loss"] = round(entry, 2)

                    # Update highest price & current stats
                    trade["highest_price"] = round(highest, 2)
                    trade["current_price"] = round(future[-1]["c"], 2)
                    trade["days_open"] = days_open
                    trade["pnl_pct"] = round((future[-1]["c"] - entry) / entry * 100, 2)

                    # ── TIME STOP ──
                    current_pnl = (future[-1]["c"] - entry) / entry * 100
                    if days_open > MAX_DAYS_NO_PROGRESS and current_pnl < MIN_PROGRESS_PCT:
                        trade.update(status="time_stop", exit_price=round(future[-1]["c"], 2),
                                     exit_date=today, r_multiple=0.0,
                                     pnl_pct=round(current_pnl, 2))

            except Exception:
                continue

    _save_trades(trades_db)
    return _portfolio_summary(trades_db["trades"])


def _portfolio_summary(trades):
    total = len(trades)
    open_trades = [t for t in trades if t["status"] == "open"]
    closed = [t for t in trades if t["status"] in ("win", "loss", "time_stop")]
    wins = [t for t in closed if t["status"] == "win"]
    losses = [t for t in closed if t["status"] in ("loss", "time_stop")]
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
