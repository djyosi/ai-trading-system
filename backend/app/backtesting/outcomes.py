def label_recommendation_outcome(recommendation, future_candles, recommendation_timestamp_ms=None):
    if recommendation.get("status") == "no_trade":
        return {
            "status": "skipped",
            "target_hit": False,
            "stop_hit": False,
            "realized_r": None,
            "skip_reason": "recommendation_was_no_trade",
        }

    candles = _future_only(future_candles, recommendation_timestamp_ms)
    entry = _entry_price(recommendation)
    stop = recommendation.get("stop_loss")
    targets = recommendation.get("targets") or []
    first_target = targets[0] if targets else None

    if entry is None or stop is None or first_target is None:
        return {
            "status": "unscorable",
            "target_hit": False,
            "stop_hit": False,
            "realized_r": None,
            "skip_reason": "missing_entry_stop_or_target",
        }

    risk_per_share = max(entry - stop, 0.01)
    max_high = max((candle.get("high") for candle in candles), default=entry)
    min_low = min((candle.get("low") for candle in candles), default=entry)
    max_favorable_excursion_r = round((max_high - entry) / risk_per_share, 2)
    max_adverse_excursion_r = round((min_low - entry) / risk_per_share, 2)

    for index, candle in enumerate(candles, start=1):
        low = candle.get("low")
        high = candle.get("high")
        if low is not None and low <= stop:
            return {
                "status": "closed",
                "target_hit": False,
                "stop_hit": True,
                "realized_r": -1.0,
                "bars_to_stop": index,
                "max_favorable_excursion_r": max_favorable_excursion_r,
                "max_adverse_excursion_r": max_adverse_excursion_r,
            }
        if high is not None and high >= first_target:
            return {
                "status": "closed",
                "target_hit": True,
                "stop_hit": False,
                "realized_r": round((first_target - entry) / risk_per_share, 2),
                "bars_to_target": index,
                "max_favorable_excursion_r": max_favorable_excursion_r,
                "max_adverse_excursion_r": max_adverse_excursion_r,
            }

    return {
        "status": "open",
        "target_hit": False,
        "stop_hit": False,
        "realized_r": None,
        "max_favorable_excursion_r": max_favorable_excursion_r,
        "max_adverse_excursion_r": max_adverse_excursion_r,
    }


def _future_only(candles, recommendation_timestamp_ms):
    if recommendation_timestamp_ms is None:
        return candles
    return [
        candle
        for candle in candles
        if candle.get("timestamp_ms") is None or candle.get("timestamp_ms") > recommendation_timestamp_ms
    ]


def _entry_price(recommendation):
    entry_zone = recommendation.get("entry_zone")
    if not entry_zone:
        return None
    return round(sum(entry_zone) / len(entry_zone), 4)
