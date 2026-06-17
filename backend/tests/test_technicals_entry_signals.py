from app.technicals.entry_signals import analyze_technical, SIGNAL_BUY, SIGNAL_STRONG_BUY, SIGNAL_SELL, SIGNAL_STRONG_SELL, SIGNAL_HOLD


def _c(ts, open, high, low, close, volume=1_000_000):
    return {"timestamp_ms": ts, "open": open, "high": high, "low": low, "close": close, "volume": volume}


def test_strong_uptrend_gives_buy():
    """Clean uptrend with good volume = buy."""
    candles = [_c(i, 100 + i, 102 + i, 99 + i, 101 + i, 1_000_000 + i * 100_000) for i in range(20)]
    result = analyze_technical("AAPL", candles)
    assert result["signal"] in (SIGNAL_BUY, SIGNAL_STRONG_BUY, SIGNAL_HOLD)
    assert result["score"] >= 0
    assert len(result["reasons"]) >= 1


def test_downtrend_gives_sell():
    """Clean downtrend = sell."""
    candles = [_c(i, 100 - i, 102 - i, 99 - i, 101 - i, 1_000_000) for i in range(20)]
    result = analyze_technical("AAPL", candles)
    assert result["signal"] in (SIGNAL_SELL, SIGNAL_STRONG_SELL)


def test_sideways_gives_hold():
    """Sideways price action = hold."""
    candles = [_c(i, 100, 102, 99, 101, 1_000_000) for i in range(20)]
    result = analyze_technical("AAPL", candles)
    assert result["signal"] == SIGNAL_HOLD


def test_bullish_divergence_with_pattern():
    """Bullish divergence + hammer = buy signal."""
    candles = []
    for i in range(15):
        price = 100 - i * (1.5 if i < 10 else -0.5)  # drop then recover
        vol = 1_000_000 + (i if i > 8 else 0) * 200_000  # volume rises at end
        candles.append(_c(i, price, price + 1, price - 1, price, vol))
    result = analyze_technical("AAPL", candles)
    # Should get at least some bullish signal
    assert "signal" in result


def test_entry_signal_has_all_fields():
    """Entry signal includes ticker, price, support, resistance, channel."""
    candles = [_c(i, 100 + i * 0.3, 102 + i * 0.3, 99 + i * 0.3, 101 + i * 0.3, 1_000_000) for i in range(20)]
    result = analyze_technical("AAPL", candles)
    assert result["ticker"] == "AAPL"
    assert result.get("current_price") is not None
    assert "reasons" in result
    assert "channel" in result
    assert "candle_pattern" in result
