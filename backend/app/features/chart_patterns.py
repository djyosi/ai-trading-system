DOJI_BODY_RATIO = 0.05
HAMMER_WICK_RATIO = 2.0
MARUBOZU_WICK_RATIO = 0.02


def _range(candle):
    return candle["high"] - candle["low"]


def _body(candle):
    return abs(candle["close"] - candle["open"])


def _upper_wick(candle):
    return candle["high"] - max(candle["open"], candle["close"])


def _lower_wick(candle):
    return min(candle["open"], candle["close"]) - candle["low"]


def _body_top(candle):
    return max(candle["open"], candle["close"])


def _body_bottom(candle):
    return min(candle["open"], candle["close"])


def _is_bullish(candle):
    return candle["close"] >= candle["open"]


def classify_candle_pattern(candle):
    crange = _range(candle)
    if crange == 0:
        return {"pattern": "none", "direction": "neutral", "strength": "none"}

    body = _body(candle)
    upper_wick = _upper_wick(candle)
    lower_wick = _lower_wick(candle)

    # Doji: tiny body relative to range
    if body / crange <= DOJI_BODY_RATIO:
        return {"pattern": "doji", "direction": "neutral", "strength": "weak"}

    # Marubozu: very small wicks, full body
    if upper_wick / crange <= MARUBOZU_WICK_RATIO and lower_wick / crange <= MARUBOZU_WICK_RATIO:
        return {"pattern": "marubozu", "direction": "bullish" if _is_bullish(candle) else "bearish", "strength": "strong"}

    # Hammer: small body at top, long lower wick, short upper wick
    if lower_wick >= HAMMER_WICK_RATIO * body and upper_wick <= 0.3 * body:
        return {"pattern": "hammer", "direction": "bullish", "strength": "moderate"}

    # Shooting star: small body at bottom, long upper wick, short lower wick
    if upper_wick >= HAMMER_WICK_RATIO * body and lower_wick <= 0.3 * body:
        return {"pattern": "shooting_star", "direction": "bearish", "strength": "moderate"}

    return {"pattern": "none", "direction": "neutral", "strength": "none"}


def classify_multi_candle_pattern(prev_candle, curr_candle):
    prev_body_top = _body_top(prev_candle)
    prev_body_bottom = _body_bottom(prev_candle)
    curr_body_top = _body_top(curr_candle)
    curr_body_bottom = _body_bottom(curr_candle)

    # Bullish engulfing: current body completely covers previous body, bullish
    if (
        curr_body_bottom <= prev_body_bottom
        and curr_body_top >= prev_body_top
        and _is_bullish(curr_candle)
    ):
        return {"pattern": "bullish_engulfing", "direction": "bullish", "strength": "strong"}

    # Bearish engulfing: current body completely covers previous body, bearish
    if (
        curr_body_bottom <= prev_body_bottom
        and curr_body_top >= prev_body_top
        and not _is_bullish(curr_candle)
    ):
        return {"pattern": "bearish_engulfing", "direction": "bearish", "strength": "strong"}

    return {"pattern": "none", "direction": "neutral", "strength": "none"}
