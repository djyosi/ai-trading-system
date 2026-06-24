"""
Technical indicator calculations for the standalone screener.
All functions take a list of candles: [{open, high, low, close, volume, timestamp_ms}]
"""


def sma(candles, period):
    """Simple Moving Average of closing prices."""
    closes = [c["close"] for c in candles[-period:] if c.get("close") is not None]
    return sum(closes) / len(closes) if closes else None


def rsi(candles, period=14):
    """Relative Strength Index."""
    closes = [c["close"] for c in candles if c.get("close") is not None]
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def bollinger_bands(candles, period=20, std=2):
    """Bollinger Bands: upper, middle (SMA), lower."""
    closes = [c["close"] for c in candles[-period:] if c.get("close") is not None]
    if len(closes) < period:
        return None, None, None
    mid = sum(closes) / period
    variance = sum((c - mid) ** 2 for c in closes) / period
    sd = variance ** 0.5
    return mid + std * sd, mid, mid - std * sd


def avg_volume(candles, period=20):
    """Average volume over period."""
    vols = [c["volume"] for c in candles[-period:] if c.get("volume") is not None]
    return sum(vols) / len(vols) if vols else None


def low_of_n(candles, n=5):
    """Lowest low in last n candles."""
    lows = [c["low"] for c in candles[-n:] if c.get("low") is not None]
    return min(lows) if lows else None


def detect_bull_flag(candles, lookback=10):
    """Detect a bull flag: sharp up move, then consolidation, then breakout."""
    if len(candles) < lookback * 2:
        return False
    pole = candles[-lookback * 2:-lookback]
    flag = candles[-lookback:]
    pole_move = (pole[-1]["close"] - pole[0]["close"]) / pole[0]["close"]
    flag_move = (flag[-1]["close"] - flag[0]["close"]) / flag[0]["close"]
    return pole_move > 0.05 and abs(flag_move) < abs(pole_move) * 0.3


def macd(candles, fast=12, slow=26, signal=9):
    """MACD line and signal line."""
    closes = [c["close"] for c in candles if c.get("close") is not None]
    if len(closes) < slow + signal:
        return None, None

    def ema(data, period):
        k = 2 / (period + 1)
        result = [data[0]]
        for price in data[1:]:
            result.append(price * k + result[-1] * (1 - k))
        return result

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    return macd_line[-1], signal_line[-1]


def detect_bullish_engulfing(candles):
    """Check if last 2 candles form a bullish engulfing."""
    if len(candles) < 2:
        return False
    prev, curr = candles[-2], candles[-1]
    return (prev["close"] < prev["open"] and
            curr["close"] > curr["open"] and
            curr["open"] < prev["close"] and
            curr["close"] > prev["open"])


def detect_three_up_days(candles):
    """Check if last 3 candles are all up days."""
    if len(candles) < 3:
        return False
    for i in range(-3, 0):
        if candles[i]["close"] <= candles[i]["open"]:
            return False
    return True


def detect_volume_rising_3(candles):
    """Check if volume has increased for 3 consecutive days."""
    if len(candles) < 3:
        return False
    for i in range(-3, -1):
        if candles[i]["volume"] is None or candles[i + 1]["volume"] is None:
            return False
        if candles[i + 1]["volume"] <= candles[i]["volume"]:
            return False
    return True


def compute_indicators(candles):
    """Compute all indicators for a candle list. Returns dict."""
    if not candles or len(candles) < 3:
        return {"error": "insufficient_data"}

    last = candles[-1]
    
    # ---- DATA FRESHNESS ----
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    last_ts = last.get("timestamp_ms", 0)
    if isinstance(last_ts, (int, float)):
        last_date = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
        days_old = (now - last_date).days
    else:
        days_old = 999
    
    # ---- LIQUIDITY ----
    recent_vols = [c.get("volume", 0) or 0 for c in candles[-10:]]
    avg_vol_10 = sum(recent_vols) / len(recent_vols) if recent_vols else 0
    last_price = last.get("close", 0) or 0
    
    # ---- INDICATORS ----
    upper, mid, lower = bollinger_bands(candles)
    sma_20 = sma(candles, 20) if len(candles) >= 20 else None
    sma_50 = sma(candles, 50) if len(candles) >= 50 else None
    sma_200 = sma(candles, 200) if len(candles) >= 200 else None
    sma_50_1d = sma(candles[:-1], 50) if len(candles) >= 51 else None
    sma_200_1d = sma(candles[:-1], 200) if len(candles) >= 201 else None
    macd_line, signal_line = macd(candles)
    macd_1d, signal_1d = macd(candles[:-1]) if len(candles) >= 27 else (None, None)
    rsi_val = rsi(candles)
    rsi_3d = rsi(candles[:-3], 14) if len(candles) >= 17 else None

    # Band width for squeeze detection
    b_width = (upper - lower) / mid if (upper and lower and mid and mid != 0) else None
    upper_10d, _, lower_10d = bollinger_bands(candles[:-10], 20, 2) if len(candles) > 25 else (None, None, None)
    b_width_10d = (upper_10d - lower_10d) / mid if (upper_10d and lower_10d and mid and mid != 0) else None

    return {
        "close": last.get("close"),
        "volume": last.get("volume"),
        "last_price": last_price,
        "avg_volume_10": avg_vol_10,
        "days_since_last_trade": days_old,
        "is_fresh": days_old <= 7,
        "is_liquid": avg_vol_10 >= 500_000 and last_price >= 5.0,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "sma_50_1d": sma_50_1d,
        "sma_200_1d": sma_200_1d,
        "rsi_14": rsi_val,
        "rsi_14_3d_ago": rsi_3d,
        "upper_band": upper,
        "middle_band": mid,
        "lower_band": lower,
        "band_width_pct": b_width,
        "band_width_10d_ago": b_width_10d,
        "avg_volume_20": avg_volume(candles, 20),
        "low_of_5": low_of_n(candles, 5),
        "low_of_20": low_of_n(candles, 20),
        "macd": macd_line,
        "signal": signal_line,
        "macd_1d": macd_1d,
        "signal_1d": signal_1d,
        "bull_flag_detected": detect_bull_flag(candles),
        "bullish_engulfing_detected": detect_bullish_engulfing(candles),
        "up_days_3": detect_three_up_days(candles),
        "volume_rising_3": detect_volume_rising_3(candles),
    }


def check_screen(indicators, screen_name):
    """Check if indicators match a screen's conditions."""
    from app.ta_screener import SCREENS
    screen = SCREENS.get(screen_name)
    if not screen:
        return False

    ind = indicators
    if ind.get("error"):
        return False

    # Global filters — every screen requires fresh, liquid data
    if not ind.get("is_fresh"):
        return False
    if not ind.get("is_liquid"):
        return False

    for condition in screen["conditions"]:
        if not _eval_condition(condition, ind):
            return False
    return True


def _eval_condition(condition, ind):
    """Evaluate a single condition string against indicators."""
    try:
        return bool(eval(condition, {"__builtins__": {}}, ind))
    except Exception:
        return False
