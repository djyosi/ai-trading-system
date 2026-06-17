from app.technicals.volume import (
    volume_trend, volume_divergence,
    TREND_RISING, TREND_FALLING, TREND_SPIKE,
    DIVERGENCE_BULLISH, DIVERGENCE_BEARISH, DIVERGENCE_NONE,
)


def _c(ts, close, volume):
    return {"timestamp_ms": ts, "open": close - 0.5, "high": close + 0.5, "low": close - 0.5, "close": close, "volume": volume}


def test_rising_volume_trend():
    candles = [_c(i, 100 + i * 0.5, 1_000_000 + i * 100_000) for i in range(15)]
    assert volume_trend(candles) == TREND_RISING


def test_falling_volume_trend():
    candles = [_c(i, 100 + i * 0.5, 1_000_000 - i * 100_000) for i in range(15)]
    assert volume_trend(candles) == TREND_FALLING


def test_volume_spike():
    """Single candle with 3x average volume = spike."""
    candles = [_c(i, 100, 1_000_000) for i in range(10)]
    candles.append(_c(10, 100, 4_000_000))
    assert volume_trend(candles[-5:]) == TREND_SPIKE


def test_bullish_divergence():
    """Price making lower low but volume making higher low = bullish divergence."""
    candles = []
    for i in range(10):
        price = 100 - i * 2  # falling price
        vol = 1_000_000 + i * 200_000  # rising volume
        candles.append(_c(i, price, vol))
    assert volume_divergence(candles) == DIVERGENCE_BULLISH


def test_bearish_divergence():
    """Price making higher high but volume making lower high = bearish divergence."""
    candles = []
    for i in range(10):
        price = 100 + i * 2  # rising price
        vol = 1_000_000 - i * 100_000  # falling volume
        candles.append(_c(i, price, vol))
    assert volume_divergence(candles) == DIVERGENCE_BEARISH


def test_no_divergence():
    """Price and volume moving together = no divergence."""
    candles = [_c(i, 100 + i, 1_000_000 + i * 100_000) for i in range(10)]
    assert volume_divergence(candles) == DIVERGENCE_NONE
