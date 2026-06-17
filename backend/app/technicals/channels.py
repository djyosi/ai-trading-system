CHANNEL_NONE = "sideways"
CHANNEL_UP = "rising"
CHANNEL_DOWN = "falling"


def detect_channel(candles, lookback=10):
    """Detect rising/falling/sideways channel from recent candles.

    Uses linear regression on highs and lows to determine trend.
    """
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    if len(recent) < 3:
        return {"type": CHANNEL_NONE, "upper": None, "lower": None}

    highs_idx = [(i, c.get("high", 0)) for i, c in enumerate(recent) if c.get("high") is not None]
    lows_idx = [(i, c.get("low", 0)) for i, c in enumerate(recent) if c.get("low") is not None]
    closes = [c.get("close") for c in recent if c.get("close") is not None]

    if len(highs_idx) < 3 or len(lows_idx) < 3 or not closes:
        return {"type": CHANNEL_NONE, "upper": None, "lower": None}

    high_slope = _slope(highs_idx)
    low_slope = _slope(lows_idx)
    avg_slope = (high_slope + low_slope) / 2

    if avg_slope > 0.3:
        channel_type = CHANNEL_UP
    elif avg_slope < -0.3:
        channel_type = CHANNEL_DOWN
    else:
        channel_type = CHANNEL_NONE

    last_high = highs_idx[-1][1]
    last_low = lows_idx[-1][1]
    last_close = closes[-1]

    return {
        "type": channel_type,
        "upper": round(last_high + avg_slope * 2, 2) if channel_type != CHANNEL_NONE else round(last_high, 2),
        "lower": round(last_low + avg_slope * 2, 2) if channel_type != CHANNEL_NONE else round(last_low, 2),
        "slope": round(avg_slope, 2),
        "current_price": last_close,
    }


def _slope(points):
    """Simple linear slope using first and last point."""
    if len(points) < 2:
        return 0
    x1, y1 = points[0]
    x2, y2 = points[-1]
    if x2 == x1:
        return 0
    return (y2 - y1) / (x2 - x1)
