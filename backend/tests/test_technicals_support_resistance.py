
from app.technicals.support_resistance import find_swing_points, cluster_levels, support_resistance


def _c(ts, open, high, low, close, volume=1_000_000):
    return {"timestamp_ms": ts, "open": open, "high": high, "low": low, "close": close, "volume": volume}


def test_find_swing_highs():
    """Local peaks within valid window should be detected."""
    # With window=2 and 8 candles, valid indices are 2..5
    candles = [
        _c(1, 100, 100, 99, 100),    # before window
        _c(2, 100, 101, 99, 100),    # before window  (higher than i0)
        _c(3, 100, 105, 99, 100),    # i=2: SWING HIGH (105 > 101, 104, 103, 102)
        _c(4, 103, 104, 99, 100),    # i=3
        _c(5, 99, 103, 97, 100),     # i=4: SWING LOW (97 < 99, 99, 99, 98)
        _c(6, 100, 102, 99, 100),    # i=5
        _c(7, 100, 101, 98, 100),    # after window
        _c(8, 100, 100, 98, 100),    # after window
    ]

    highs, lows = find_swing_points(candles, window=2)
    assert 105 in highs, f"Expected 105 in highs, got {highs}"
    assert 97 in lows, f"Expected 97 in lows, got {lows}"


def test_find_swing_lows():
    """Downtrend with local valleys should find swing lows."""
    # With window=2 and 8 candles, valid indices are 2..5
    candles = [
        _c(1, 102, 103, 101, 102),
        _c(2, 101, 102, 99, 100),    # before window
        _c(3, 100, 100, 95, 97),     # i=2: SWING LOW (95 < 99, 100, 97, 98)
        _c(4, 97, 99, 97, 98),       # i=3
        _c(5, 98, 100, 98, 99),      # i=4
        _c(6, 99, 101, 96, 100),     # i=5
        _c(7, 100, 100, 99, 100),
        _c(8, 100, 100, 99, 100),
    ]

    highs, lows = find_swing_points(candles, window=2)
    assert 95 in lows, f"Expected 95 in lows, got {lows}"


def test_cluster_levels():
    """Nearby prices should cluster into one level."""
    levels = cluster_levels([100.5, 101.0, 101.5, 105.0, 105.2, 110.0])

    assert len(levels) == 3  # 100-101 cluster, 105 cluster, 110
    assert any(abs(level["level"] - 101) < 1 for level in levels)
    assert any(abs(level["level"] - 105) < 1 for level in levels)
    assert any(abs(level["level"] - 110) < 1 for level in levels)


def test_support_resistance_full():
    """Integration: find S/R levels from a chart with swings."""
    candles = []
    for i, (high_val, low_val) in enumerate([
        (100, 98), (103, 99), (104, 101), (102, 98), (106, 103),
        (108, 104), (106, 102), (110, 105), (109, 104),
    ]):
        mid = (high_val + low_val) / 2
        candles.append(_c(i, mid, high_val, low_val, mid))

    sr = support_resistance(candles)

    assert "support" in sr
    assert "resistance" in sr
    assert sr.get("support") or sr.get("resistance"), "Need at least one level"


def test_supports_are_below_current_price():
    """Support levels must be below current price."""
    candles = [_c(i, 100 + i, 102 + i, 98 + i, 101 + i) for i in range(10)]

    sr = support_resistance(candles)

    for s in sr["support"]:
        assert s["level"] < sr["current_price"], f"{s['level']} >= {sr['current_price']}"


def test_resistances_are_above_current_price():
    """Resistance levels must be above current price."""
    candles = [_c(i, 100 + i, 102 + i, 98 + i, 101 + i) for i in range(10)]

    sr = support_resistance(candles)

    for r in sr["resistance"]:
        assert r["level"] > sr["current_price"], f"{r['level']} <= {sr['current_price']}"
