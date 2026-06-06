def classify_etf_trend(candles, lookback=5):
    if not candles or len(candles) < lookback:
        return "neutral"
    window = candles[-lookback:]
    closes = [candle.get("close") for candle in window if candle.get("close") is not None]
    if len(closes) < lookback:
        return "neutral"

    moving_average = sum(closes) / len(closes)
    latest_close = closes[-1]
    slope = closes[-1] - closes[0]

    if latest_close > moving_average and slope > 0:
        return "up"
    if latest_close < moving_average and slope < 0:
        return "down"
    return "neutral"


def summarize_market_context(etf_candles):
    spy_trend = classify_etf_trend(etf_candles.get("SPY", []))
    qqq_trend = classify_etf_trend(etf_candles.get("QQQ", []))
    iwm_trend = classify_etf_trend(etf_candles.get("IWM", []))

    if spy_trend == "up" and qqq_trend == "up":
        risk_context = "supportive"
    elif spy_trend == "down" and qqq_trend == "down":
        risk_context = "risk_off"
    else:
        risk_context = "mixed"

    return {
        "spy_trend": spy_trend,
        "qqq_trend": qqq_trend,
        "iwm_trend": iwm_trend,
        "risk_context": risk_context,
    }
