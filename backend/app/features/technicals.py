def calculate_gap_percent(previous_close, current_price):
    if previous_close is None or previous_close == 0 or current_price is None:
        return None
    return round(((current_price - previous_close) / previous_close) * 100, 2)


def calculate_vwap(candles):
    total_volume = 0
    total_price_volume = 0
    for candle in candles:
        volume = candle.get("volume") or 0
        typical_price = ((candle.get("high") or 0) + (candle.get("low") or 0) + (candle.get("close") or 0)) / 3
        total_volume += volume
        total_price_volume += typical_price * volume
    if total_volume == 0:
        return None
    return round(total_price_volume / total_volume, 2)


def calculate_atr_percent(candles, period=14):
    if not candles:
        return None
    window = candles[-period:]
    true_ranges = []
    previous_close = None
    for candle in window:
        high = candle.get("high")
        low = candle.get("low")
        close = candle.get("close")
        if high is None or low is None:
            continue
        if previous_close is None:
            true_range = high - low
        else:
            true_range = max(high - low, abs(high - previous_close), abs(low - previous_close))
        true_ranges.append(true_range)
        previous_close = close
    latest_close = window[-1].get("close")
    if not true_ranges or not latest_close:
        return None
    atr = sum(true_ranges) / len(true_ranges)
    return round((atr / latest_close) * 100, 2)


def calculate_opening_range(candles, candle_count=3):
    window = candles[:candle_count]
    if not window:
        return {"opening_range_high": None, "opening_range_low": None}
    return {
        "opening_range_high": max(candle.get("high") for candle in window),
        "opening_range_low": min(candle.get("low") for candle in window),
    }


def calculate_prior_levels(candles):
    prior = candles[:-1] if len(candles) > 1 else candles
    if not prior:
        return {"prior_high": None, "prior_low": None}
    return {
        "prior_high": max(candle.get("high") for candle in prior),
        "prior_low": min(candle.get("low") for candle in prior),
    }


def calculate_technical_score(daily_candles):
    """TA score from daily candles (-7 to +7). Uses S/R, channel, volume, patterns.

    Returns None when insufficient data.
    """
    if not daily_candles or len(daily_candles) < 25:
        return None

    from app.technicals.entry_signals import analyze_technical
    result = analyze_technical("", daily_candles)
    return result.get("score")
