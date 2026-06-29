"""
Technical indicator calculations for the standalone screener.
All functions take a list of candles: [{open, high, low, close, volume, timestamp_ms}]
"""


def sma(candles, period):
    closes = [c["close"] for c in candles[-period:] if c.get("close") is not None]
    return sum(closes) / len(closes) if closes else None


def rsi(candles, period=14):
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
    closes = [c["close"] for c in candles[-period:] if c.get("close") is not None]
    if len(closes) < period:
        return None, None, None
    mid = sum(closes) / period
    variance = sum((c - mid) ** 2 for c in closes) / period
    sd = variance ** 0.5
    return mid + std * sd, mid, mid - std * sd


def avg_volume(candles, period=20):
    vols = [c["volume"] for c in candles[-period:] if c.get("volume") is not None]
    return sum(vols) / len(vols) if vols else None


def low_of_n(candles, n=5):
    lows = [c["low"] for c in candles[-n:] if c.get("low") is not None]
    return min(lows) if lows else None


def detect_bull_flag(candles, lookback=10):
    if len(candles) < lookback * 2:
        return False
    pole = candles[-lookback * 2:-lookback]
    flag = candles[-lookback:]
    pole_move = (pole[-1]["close"] - pole[0]["close"]) / pole[0]["close"]
    flag_move = (flag[-1]["close"] - flag[0]["close"]) / flag[0]["close"]
    return pole_move > 0.05 and abs(flag_move) < abs(pole_move) * 0.3


def macd(candles, fast=12, slow=26, signal=9):
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
    if len(candles) < 2:
        return False
    prev, curr = candles[-2], candles[-1]
    return (prev["close"] < prev["open"] and
            curr["close"] > curr["open"] and
            curr["open"] < prev["close"] and
            curr["close"] > prev["open"])


def detect_three_up_days(candles):
    if len(candles) < 3:
        return False
    for i in range(-3, 0):
        if candles[i]["close"] <= candles[i]["open"]:
            return False
    return True


def detect_volume_rising_3(candles):
    if len(candles) < 3:
        return False
    for i in range(-3, -1):
        if candles[i]["volume"] is None or candles[i + 1]["volume"] is None:
            return False
        if candles[i + 1]["volume"] <= candles[i]["volume"]:
            return False
    return True


# ── CHART PATTERN DETECTION ─────────────────────────────────────

def _similar(a, b, tolerance=0.02):
    """True if a and b are within tolerance% of each other."""
    if not a or not b:
        return False
    return abs(a - b) / max(a, b) <= tolerance


def detect_double_bottom(candles, window=5):
    """Two lows at similar price levels, with a bounce in between."""
    if len(candles) < window * 3 + 5:
        return False
    mid = len(candles) // 2
    left = candles[mid - window:mid]
    right = candles[mid:mid + window]
    center = candles[mid - 2:mid + 2]
    left_low = min(c["low"] for c in left)
    right_low = min(c["low"] for c in right)
    center_high = max(c["close"] for c in center)
    bounce = (center_high - max(left_low, right_low)) / max(left_low, right_low)
    return _similar(left_low, right_low, 0.03) and bounce > 0.03


def detect_double_top(candles, window=5):
    """Two highs at similar price levels, with a drop in between."""
    if len(candles) < window * 3 + 5:
        return False
    mid = len(candles) // 2
    left = candles[mid - window:mid]
    right = candles[mid:mid + window]
    center = candles[mid - 2:mid + 2]
    left_high = max(c["high"] for c in left)
    right_high = max(c["high"] for c in right)
    center_low = min(c["close"] for c in center)
    drop = (max(left_high, right_high) - center_low) / max(left_high, right_high)
    return _similar(left_high, right_high, 0.03) and drop > 0.03


def detect_head_shoulders(candles, window=3):
    """Head and shoulders: left shoulder, higher head, right shoulder at similar level."""
    if len(candles) < window * 4 + 5:
        return False
    left = candles[-window * 4:-window * 3]
    head = candles[-window * 3:-window * 2]
    right = candles[-window * 2:-window]
    neck = candles[-window:]
    if not left or not head or not right:
        return False
    left_high = max(c["high"] for c in left)
    head_high = max(c["high"] for c in head)
    right_high = max(c["high"] for c in right)
    neck_low = min(c["low"] for c in neck)
    return (head_high > left_high and
            head_high > right_high and
            _similar(left_high, right_high, 0.05) and
            neck_low < min(c["low"] for c in left))


def detect_channel_up(candles, lookback=20):
    """Higher highs and higher lows = rising channel."""
    if len(candles) < lookback:
        return False
    recent = candles[-lookback:]
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    return (highs[-1] > highs[0] * 1.05 and
            lows[-1] > lows[0] * 1.02)


def detect_channel_down(candles, lookback=20):
    """Lower highs and lower lows = falling channel."""
    if len(candles) < lookback:
        return False
    recent = candles[-lookback:]
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    return (highs[-1] < highs[0] * 0.95 and
            lows[-1] < lows[0] * 0.98)


def detect_near_support(candles, lookback=20, pct=3.0):
    """Price near recent support level."""
    if len(candles) < lookback:
        return False
    recent_low = min(c["low"] for c in candles[-lookback:])
    current = candles[-1]["close"]
    proximity = (current - recent_low) / recent_low * 100
    return 0 <= proximity <= pct


def detect_near_resistance(candles, lookback=20, pct=3.0):
    """Price near recent resistance level."""
    if len(candles) < lookback:
        return False
    recent_high = max(c["high"] for c in candles[-lookback:])
    current = candles[-1]["close"]
    proximity = (recent_high - current) / current * 100
    return 0 <= proximity <= pct


def detect_volume_divergence_bullish(candles, lookback=14):
    """Price making lower lows but volume declining = bullish divergence."""
    if len(candles) < lookback:
        return False
    recent = candles[-lookback:]
    lows = [c["low"] for c in recent]
    vols = [c["volume"] for c in recent]
    first_half_vol = sum(vols[:len(vols)//2]) / (len(vols)//2)
    second_half_vol = sum(vols[len(vols)//2:]) / (len(vols) - len(vols)//2)
    return lows[-1] < lows[0] and second_half_vol < first_half_vol * 0.7


def compute_indicators(candles):
    """Compute all indicators for a candle list. Returns dict."""
    if not candles or len(candles) < 3:
        return {"error": "insufficient_data"}

    last = candles[-1]

    # Data freshness
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    last_ts = last.get("timestamp_ms", 0)
    if isinstance(last_ts, (int, float)):
        last_date = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
        days_old = (now - last_date).days
    else:
        days_old = 999

    # Liquidity
    recent_vols = [c.get("volume", 0) or 0 for c in candles[-10:]]
    avg_vol_10 = sum(recent_vols) / len(recent_vols) if recent_vols else 0
    last_price = last.get("close", 0) or 0

    # Indicators
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
        # Chart patterns
        "double_bottom_detected": detect_double_bottom(candles),
        "double_top_detected": detect_double_top(candles),
        "head_shoulders_detected": detect_head_shoulders(candles),
        "channel_up_detected": detect_channel_up(candles),
        "channel_down_detected": detect_channel_down(candles),
        "near_support": detect_near_support(candles),
        "near_resistance": detect_near_resistance(candles),
        "volume_divergence_bullish": detect_volume_divergence_bullish(candles),
    }


def check_screen(indicators, screen_name):
    from app.ta_screener import SCREENS
    screen = SCREENS.get(screen_name)
    if not screen:
        return False
    ind = indicators
    if ind.get("error"):
        return False
    if not ind.get("is_fresh"):
        return False
    if not ind.get("is_liquid"):
        return False
    for condition in screen["conditions"]:
        if not _eval_condition(condition, ind):
            return False
    return True


def _eval_condition(condition, ind):
    try:
        return bool(eval(condition, {"__builtins__": {}}, ind))
    except Exception:
        return False
