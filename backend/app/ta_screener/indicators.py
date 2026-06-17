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


def compute_indicators(candles):
    """Compute all indicators for a candle list. Returns dict."""
    if not candles or len(candles) < 3:
        return {"error": "insufficient_data"}

    last = candles[-1]
    upper, mid, lower = bollinger_bands(candles)
    sma_50 = sma(candles, 50) if len(candles) >= 50 else None
    sma_200 = sma(candles, 200) if len(candles) >= 200 else None
    sma_50_1d = sma(candles[:-1], 50) if len(candles) >= 51 else None
    sma_200_1d = sma(candles[:-1], 200) if len(candles) >= 201 else None

    return {
        "close": last.get("close"),
        "volume": last.get("volume"),
        "sma_50": sma_50,
        "sma_200": sma_200,
        "sma_50_1d": sma_50_1d,
        "sma_200_1d": sma_200_1d,
        "rsi_14": rsi(candles),
        "upper_band": upper,
        "middle_band": mid,
        "lower_band": lower,
        "avg_volume_20": avg_volume(candles, 20),
        "low_of_5": low_of_n(candles, 5),
        "bull_flag_detected": detect_bull_flag(candles),
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
