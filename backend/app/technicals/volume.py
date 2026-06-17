TREND_RISING = "rising"
TREND_FALLING = "falling"
TREND_FLAT = "flat"
TREND_SPIKE = "spike"

DIVERGENCE_BULLISH = "bullish"
DIVERGENCE_BEARISH = "bearish"
DIVERGENCE_NONE = "none"

SPIKE_THRESHOLD = 2.5


def volume_trend(candles, lookback=10):
    """Determine volume trend from recent candles: rising, falling, flat, or spike."""
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    volumes = [c.get("volume") for c in recent if c.get("volume") is not None]

    if len(volumes) < 3:
        return TREND_FLAT

    avg = sum(volumes[:-1]) / len(volumes[:-1])
    if avg > 0 and volumes[-1] / avg >= SPIKE_THRESHOLD:
        return TREND_SPIKE

    first_half = sum(volumes[:len(volumes) // 2])
    second_half = sum(volumes[len(volumes) // 2:])

    if second_half > first_half * 1.2:
        return TREND_RISING
    if second_half < first_half * 0.8:
        return TREND_FALLING
    return TREND_FLAT


def volume_divergence(candles, lookback=10):
    """Check for bullish/bearish volume divergence.

    Bullish divergence: price makes lower low, volume makes higher low.
    Bearish divergence: price makes higher high, volume makes lower high.
    """
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    if len(recent) < 5:
        return DIVERGENCE_NONE

    closes = [c.get("close") for c in recent if c.get("close") is not None]
    volumes = [c.get("volume") for c in recent if c.get("volume") is not None]

    if len(closes) < 5 or len(volumes) < 5:
        return DIVERGENCE_NONE

    price_first_half = sum(closes[:len(closes) // 2]) / (len(closes) // 2)
    price_second_half = sum(closes[len(closes) // 2:]) / (len(closes) - len(closes) // 2)
    vol_first_half = sum(volumes[:len(volumes) // 2]) / (len(volumes) // 2)
    vol_second_half = sum(volumes[len(volumes) // 2:]) / (len(volumes) - len(volumes) // 2)

    if price_second_half < price_first_half and vol_second_half > vol_first_half:
        return DIVERGENCE_BULLISH
    if price_second_half > price_first_half and vol_second_half < vol_first_half:
        return DIVERGENCE_BEARISH
    return DIVERGENCE_NONE
