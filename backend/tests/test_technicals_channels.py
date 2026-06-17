from app.technicals.channels import detect_channel, CHANNEL_NONE, CHANNEL_UP, CHANNEL_DOWN


def _c(ts, open, high, low, close, volume=1_000_000):
    return {"timestamp_ms": ts, "open": open, "high": high, "low": low, "close": close, "volume": volume}


def test_rising_channel_detected():
    """Higher highs and higher lows = rising channel."""
    candles = [_c(i, 100 + i, 102 + i, 99 + i, 101 + i) for i in range(15)]
    result = detect_channel(candles)
    assert result["type"] == CHANNEL_UP


def test_falling_channel_detected():
    """Lower highs and lower lows = falling channel."""
    candles = [_c(i, 100 - i, 102 - i, 99 - i, 101 - i) for i in range(15)]
    result = detect_channel(candles)
    assert result["type"] == CHANNEL_DOWN


def test_sideways_no_channel():
    """No clear trend = no channel."""
    candles = [_c(i, 100, 102, 99, 101) for i in range(15)]
    result = detect_channel(candles)
    assert result["type"] == CHANNEL_NONE


def test_channel_has_upper_and_lower():
    """Channel should define upper/lower boundaries."""
    candles = [_c(i, 100 + i, 102 + i, 99 + i, 101 + i) for i in range(15)]
    result = detect_channel(candles)
    assert result.get("upper") is not None
    assert result.get("lower") is not None
    assert result["upper"] > result["lower"]


def test_price_in_channel():
    """Channel boundaries should contain recent prices."""
    candles = [_c(i, 100 + i, 102 + i, 99 + i, 101 + i) for i in range(15)]
    result = detect_channel(candles)
    last = candles[-1]
    assert result["lower"] <= last["close"] <= result["upper"]
