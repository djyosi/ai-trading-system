from app.scanner.service import build_features


def _snapshot(price=100.0, prev_close=99.0, bid=99.95, ask=100.05, volume=5_000_000):
    return {"price": price, "previous_close": prev_close, "bid": bid, "ask": ask, "volume": volume}


def _c(open, high, low, close, volume=5_000_000, ts=None):
    return {"open": open, "high": high, "low": low, "close": close, "volume": volume, "timestamp_ms": ts or 1000000}


def test_build_features_includes_chart_pattern():
    """A candle with a hammer pattern should produce chart_pattern feature."""
    daily = [_c(100, 102, 99, 101, ts=1)]
    # Hammer: small body at top, long lower wick, small upper wick
    current = _c(open=100.0, high=100.6, low=97.0, close=100.5)
    intraday = [current]

    features = build_features(_snapshot(), daily, intraday)

    assert "chart_pattern" in features
    assert features["chart_pattern"]["pattern"] == "hammer"


def test_build_features_no_pattern_for_normal_candle():
    """Normal candle without clear pattern should have none/chart_pattern."""
    daily = [_c(100, 102, 99, 101, ts=1)]
    current = _c(open=100.0, high=101.5, low=99.5, close=100.8)
    intraday = [current]

    features = build_features(_snapshot(), daily, intraday)

    assert features["chart_pattern"]["pattern"] in ("none", "neutral")


def test_build_features_multi_candle_bullish_engulfing():
    """Two candles forming a bullish engulfing should be detected."""
    daily = [_c(100, 102, 99, 101, ts=1)]
    prev = _c(open=102.0, high=103.0, low=101.0, close=101.5, ts=2)
    curr = _c(open=101.0, high=104.0, low=100.5, close=103.0, ts=3)
    intraday = [prev, curr]

    features = build_features(_snapshot(), daily, intraday)

    assert features["chart_pattern"]["pattern"] == "bullish_engulfing"
