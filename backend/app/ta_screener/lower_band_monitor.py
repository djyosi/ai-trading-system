"""
SPY Lower Bollinger Band Monitor
--------------------------------
Checks if SPY is approaching (within 1%) or touching the lower Bollinger Band.
Prints alert when condition met — designed for cron delivery to Hermes chat.

Run: python -m app.ta_screener.lower_band_monitor

State tracking in runtime/spy_lower_band_state.json to avoid duplicate alerts.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ── paths ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_FILE = REPO_ROOT / "runtime" / "spy_lower_band_state.json"

TICKER = "SPY"
DISTANCE_PCT = 0.01       # 1% above lower band
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

# ── helpers ────────────────────────────────────────────────────────────


def load_state():
    """Load alert state. Returns dict with keys: last_alert_date, was_near_band."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_alert_date": None, "was_near_band": False, "current_session_active": False}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def bollinger_bands(closes):
    """SMA + 2 std dev Bollinger Bands."""
    if len(closes) < BOLLINGER_PERIOD:
        return None, None, None
    recent = closes[-BOLLINGER_PERIOD:]
    mid = sum(recent) / BOLLINGER_PERIOD
    variance = sum((c - mid) ** 2 for c in recent) / BOLLINGER_PERIOD
    sd = variance ** 0.5
    return mid + BOLLINGER_STD * sd, mid, mid - BOLLINGER_STD * sd


def market_is_open():
    """Check if US market is open (Mon-Fri, 09:30-16:00 ET)."""
    now = datetime.now(timezone.utc)
    weekday = now.weekday()  # Mon=0
    if weekday > 4:  # weekend
        return False
    # Convert 09:30 ET / 16:00 ET to UTC
    # ET is UTC-4 during EDT (summer), UTC-5 during EST
    # Current date: June 2026 = EDT = UTC-4
    et_offset = -4  # EDT
    now_et_hour = now.hour + et_offset
    now_et_min = now.minute
    et_total_min = now_et_hour * 60 + now_et_min
    market_open = 9 * 60 + 30   # 09:30 ET
    market_close = 16 * 60       # 16:00 ET
    return market_open <= et_total_min < market_close


def et_now_str():
    """Return human-readable ET timestamp."""
    now = datetime.now(timezone.utc)
    et_offset = -4  # EDT
    from datetime import timedelta
    et_time = now + timedelta(hours=et_offset)
    return et_time.strftime("%H:%M ET")


# ── main ───────────────────────────────────────────────────────────────


def main():
    api_key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("MASSIVE_APIKEY")
    if not api_key:
        print("❌ MASSIVE_API_KEY not found. Set in .env or environment.")
        sys.exit(1)

    if not market_is_open():
        # silently exit outside market hours
        sys.exit(0)

    state = load_state()
    today = datetime.now(timezone.utc).date().isoformat()

    # Reset daily state at start of each day
    if state.get("last_alert_date") != today:
        state = {"last_alert_date": None, "was_near_band": False, "current_session_active": False}

    # ── fetch SPY daily candles ──
    try:
        end = datetime.now(timezone.utc).date().isoformat()
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"https://api.massive.com/v2/aggs/ticker/{TICKER}/range/1/day/2025-09-01/{end}",
                params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
            )
        if resp.status_code != 200:
            print(f"⚠️ Massive API error: {resp.status_code}")
            sys.exit(1)

        payload = resp.json()
        raw = payload.get("results", [])
        if len(raw) < BOLLINGER_PERIOD:
            print(f"⚠️ Not enough data: {len(raw)} candles")
            sys.exit(1)

        closes = [r["c"] for r in raw]
        last = raw[-1]
        close = last["c"]
        volume = last["v"]
        _ = last["t"]  # timestamp, unused

    except Exception as e:
        print(f"⚠️ Fetch error: {e}")
        sys.exit(1)

    # ── compute Bollinger Bands ──
    upper, mid, lower = bollinger_bands(closes)
    if lower is None:
        print("⚠️ Could not compute Bollinger Bands")
        sys.exit(1)

    # ── check condition ──
    # "approaching" = close within 1% above the lower band, or already below
    touch_threshold = lower * (1 + DISTANCE_PCT)
    is_near_band = close <= touch_threshold
    is_below_band = close < lower
    distance_pct = ((close - lower) / lower) * 100 if lower else 0

    if is_near_band:
        # Only alert once per "session" (alert fires, then wait for price to recover >2% and enter again)
        if not state.get("current_session_active"):
            state["last_alert_date"] = today
            state["was_near_band"] = True
            state["current_session_active"] = True
            save_state(state)

            below_tag = " 📉 BELOW band!" if is_below_band else ""
            print("🚨 **SPY Bollinger Alert** 🚨")
            print("")
            print(f"  Close:     ${close:.2f}")
            print(f"  Lower BB:  ${lower:.2f}")
            print(f"  Middle BB: ${mid:.2f}")
            print(f"  Upper BB:  ${upper:.2f}")
            print(f"  Distance:  {distance_pct:+.2f}% from lower band{below_tag}")
            print(f"  Threshold: within {DISTANCE_PCT*100:.0f}% (${touch_threshold:.2f})")
            print(f"  Volume:    {volume:,}")
            print(f"  Time:      {et_now_str()}")
            print("")
            print("📊 Check dashboard for full analysis.")
        else:
            # Already alerted this session — stay quiet
            pass

    else:
        # Price recovered: reset session if it moved more than 2% away from lower band
        recovery_threshold = lower * (1 + DISTANCE_PCT * 2)  # 2% away = recovered
        if close > recovery_threshold:
            if state.get("current_session_active"):
                state["current_session_active"] = False
                state["was_near_band"] = False
                save_state(state)


if __name__ == "__main__":
    main()
