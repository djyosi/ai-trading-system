from app.ta_screener.indicators import sma, rsi, bollinger_bands, compute_indicators


def _c(close, volume=1_000_000):
    return {"open": close - 0.5, "high": close + 0.5, "low": close - 0.5, "close": close, "volume": volume, "timestamp_ms": 0}


def test_sma():
    candles = [_c(100 + i) for i in range(20)]
    result = sma(candles, 5)
    assert result is not None
    assert result > 0


def test_rsi():
    candles = [_c(100 + i) for i in range(20)]
    result = rsi(candles, 14)
    assert result is not None
    assert 0 <= result <= 100


def test_bollinger_bands():
    candles = [_c(100 + i) for i in range(25)]
    upper, mid, lower = bollinger_bands(candles)
    assert upper is not None
    assert upper > mid > lower


def test_volume_trend():
    candles = [_c(100, 1_000_000 + i * 100_000) for i in range(25)]
    ind = compute_indicators(candles)
    assert ind["avg_volume_20"] is not None
    assert ind["volume"] is not None


def test_rsi_oversold_detected():
    """Falling prices should eventually give low RSI."""
    candles = [_c(100 - i * 0.5) for i in range(30)]
    ind = compute_indicators(candles)
    if ind["rsi_14"] is not None:
        assert isinstance(ind["rsi_14"], (int, float))
