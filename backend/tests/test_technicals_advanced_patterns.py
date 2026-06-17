from app.technicals.advanced_patterns import (
    detect_double_top,
    detect_double_bottom,
    detect_head_shoulders,
    detect_flag,
    analyze_advanced_patterns,
    PATTERN_BULL_FLAG,
    PATTERN_BEAR_FLAG,
)


def _c(ts, open, high, low, close, volume=1_000_000):
    return {"timestamp_ms": ts, "open": open, "high": high, "low": low, "close": close, "volume": volume}


def test_double_top_detected():
    """Two peaks at similar level = double top (bearish)."""
    candles = [
        _c(1, 100, 101, 99, 100),
        _c(2, 100, 105, 99, 104),
        _c(3, 104, 110, 103, 108),   # peak 1
        _c(4, 108, 105, 103, 104),   # pullback
        _c(5, 104, 109, 103, 107),   # peak 2
        _c(6, 107, 105, 102, 103),   # breakdown
    ]
    result = detect_double_top(candles, window=1)
    assert result["detected"] is True


def test_double_bottom_detected():
    """Two troughs at similar level = double bottom (bullish)."""
    candles = [
        _c(1, 100, 101, 99, 100),
        _c(2, 100, 102, 94, 101),     # trough 1 (94)
        _c(3, 101, 105, 100, 104),    # bounce
        _c(4, 104, 106, 93.5, 105),   # trough 2 (93.5 ≈ 94)
        _c(5, 105, 110, 104, 109),    # breakout
    ]
    result = detect_double_bottom(candles, window=1)
    assert result["detected"] is True


def test_head_shoulders_detected():
    """Higher peak between two lower peaks = head & shoulders top."""
    candles = [
        _c(1, 100, 101, 99, 100),
        _c(2, 100, 105, 99, 104),    # left shoulder (105)
        _c(3, 104, 107, 100, 106),   # dip
        _c(4, 106, 115, 105, 113),   # head (115, higher)
        _c(5, 113, 108, 106, 107),   # dip
        _c(6, 107, 104, 101, 103),   # right shoulder (104 ≈ 105)
        _c(7, 103, 104, 98, 99),     # breakdown
    ]
    result = detect_head_shoulders(candles, window=1)
    assert result["detected"] is True


def test_bull_flag_detected():
    """Sharp up move then consolidation = bull flag."""
    candles = (
        [_c(i, 100 + i * 3, 101 + i * 3, 99 + i * 3, 100 + i * 3, 2_000_000) for i in range(5)]  # pole
        + [_c(5 + i, 114 - i * 0.3, 116 - i * 0.2, 113 - i * 0.3, 115 - i * 0.3, 1_000_000) for i in range(5)]  # flag
    )
    result = detect_flag(candles)
    assert result["detected"] is True
    assert result["pattern"] == PATTERN_BULL_FLAG


def test_bear_flag_detected():
    """Sharp down move then consolidation = bear flag."""
    candles = (
        [_c(i, 100 - i * 3, 101 - i * 3, 99 - i * 3, 100 - i * 3, 2_000_000) for i in range(5)]  # pole down
        + [_c(5 + i, 85 + i * 0.3, 87 + i * 0.2, 84 + i * 0.3, 86 + i * 0.3, 1_000_000) for i in range(5)]  # flag up
    )
    result = detect_flag(candles)
    assert result["detected"] is True
    assert result["pattern"] == PATTERN_BEAR_FLAG


def test_analyze_advanced_patterns_returns_all():
    """Integration: check all advanced patterns at once."""
    candles = [_c(i, 100 + i * 0.5, 102 + i * 0.5, 99 + i * 0.5, 101 + i * 0.5, 1_000_000) for i in range(20)]
    result = analyze_advanced_patterns(candles)
    assert len(result) == 5  # double_top, double_bottom, hs, flag, best
    for r in result:
        assert "pattern" in r
        assert "detected" in r
