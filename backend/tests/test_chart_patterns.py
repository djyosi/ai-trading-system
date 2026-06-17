from app.features.chart_patterns import classify_candle_pattern, classify_multi_candle_pattern


def _c(open, high, low, close, volume=5_000_000):
    return {"open": open, "high": high, "low": low, "close": close, "volume": volume}


def _body(candle):
    return abs(candle["close"] - candle["open"])


def test_doji_classification():
    """Doji: open ≈ close, tiny body relative to range"""
    candle = _c(open=100.0, high=102.0, low=98.0, close=100.05)

    result = classify_candle_pattern(candle)

    assert result["pattern"] == "doji"
    assert result["direction"] == "neutral"
    assert result["strength"] == "weak"


def test_long_legged_doji():
    """Long-legged doji with larger range"""
    candle = _c(open=100.0, high=105.0, low=95.0, close=100.1)

    result = classify_candle_pattern(candle)

    assert result["pattern"] == "doji"
    assert result["direction"] == "neutral"


def test_not_doji_when_body_too_large():
    """Body > 5% of range = not doji"""
    candle = _c(open=100.0, high=102.0, low=99.0, close=101.5)

    result = classify_candle_pattern(candle)

    assert result["pattern"] != "doji"


def test_hammer_classification():
    """Hammer: small body at top, lower wick ≥ 2x body, small upper wick"""
    candle = _c(open=100.0, high=100.6, low=97.0, close=100.5)

    result = classify_candle_pattern(candle)

    assert result["pattern"] == "hammer"
    assert result["direction"] == "bullish"
    assert result["strength"] == "moderate"


def test_shooting_star_classification():
    """Shooting star: small body at bottom, upper wick ≥ 2x body, small lower wick"""
    candle = _c(open=100.0, high=104.0, low=99.65, close=99.7)

    result = classify_candle_pattern(candle)

    assert result["pattern"] == "shooting_star"
    assert result["direction"] == "bearish"
    assert result["strength"] == "moderate"


def test_marubozu_classification():
    """Marubozu: full body, no wicks"""
    candle = _c(open=100.0, high=105.0, low=100.0, close=105.0)

    result = classify_candle_pattern(candle)

    assert result["pattern"] == "marubozu"
    assert result["strength"] == "strong"


def test_bullish_engulfing():
    """Bullish engulfing: current open ≤ prev close, current close ≥ prev open"""
    prev = _c(open=102.0, high=103.0, low=101.0, close=101.5)
    curr = _c(open=101.0, high=104.0, low=100.5, close=103.0)

    result = classify_multi_candle_pattern(prev, curr)

    assert result["pattern"] == "bullish_engulfing"
    assert result["direction"] == "bullish"
    assert result["strength"] == "strong"


def test_bearish_engulfing():
    """Bearish engulfing: current open ≥ prev close, current close ≤ prev open"""
    prev = _c(open=100.0, high=101.0, low=99.0, close=100.5)
    curr = _c(open=101.0, high=101.5, low=98.0, close=99.0)

    result = classify_multi_candle_pattern(prev, curr)

    assert result["pattern"] == "bearish_engulfing"
    assert result["direction"] == "bearish"
    assert result["strength"] == "strong"


def test_no_pattern_for_normal_candle():
    """Normal candle without clear pattern returns none"""
    candle = _c(open=100.0, high=101.5, low=99.5, close=100.8)

    result = classify_candle_pattern(candle)

    assert result["pattern"] == "none"
    assert result["direction"] == "neutral"


def test_neutral_candle():
    """Neutral: small body, wicks on both sides, not quite hammer or doji"""
    candle = _c(open=100.0, high=101.5, low=99.0, close=100.3)

    result = classify_candle_pattern(candle)

    assert result["pattern"] in ("neutral", "none")


def test_missing_open_returns_none_safely():
    """Candle without open field should not crash."""
    candle = {"high": 102, "low": 98, "close": 100}

    result = classify_candle_pattern(candle)

    assert result["pattern"] == "none"


def test_missing_fields_returns_none_safely():
    """Completely malformed candle should not crash."""
    result = classify_candle_pattern({"ticker": "AAPL"})

    assert result["pattern"] == "none"
