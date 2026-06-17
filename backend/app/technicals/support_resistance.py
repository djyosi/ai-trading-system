CLUSTER_TOLERANCE = 0.02  # 2%


def find_swing_points(candles, window=3):
    """Find swing highs and lows from a list of candles.

    A swing high is a candle whose high is higher than `window` candles
    on each side. A swing low is a candle whose low is lower.
    """
    highs = []
    lows = []
    for i in range(window, len(candles) - window):
        current_high = candles[i].get("high")
        current_low = candles[i].get("low")
        if current_high is None or current_low is None:
            continue
        is_swing_high = all(
            current_high >= candles[j].get("high", 0) for j in range(i - window, i + window + 1) if j != i
        )
        is_swing_low = all(
            current_low <= candles[j].get("low", float("inf")) for j in range(i - window, i + window + 1) if j != i
        )
        if is_swing_high:
            highs.append(current_high)
        if is_swing_low:
            lows.append(current_low)
    return highs, lows


def cluster_levels(levels, tolerance=CLUSTER_TOLERANCE):
    """Cluster nearby price levels. Returns list of {level, strength, touches}."""
    if not levels:
        return []

    sorted_levels = sorted(levels)
    clusters = []
    current_cluster = [sorted_levels[0]]

    for price in sorted_levels[1:]:
        avg = sum(current_cluster) / len(current_cluster)
        if abs(price - avg) / max(avg, 1) <= tolerance:
            current_cluster.append(price)
        else:
            clusters.append(current_cluster)
            current_cluster = [price]
    clusters.append(current_cluster)

    return [
        {"level": round(sum(c) / len(c), 2), "touches": len(c), "strength": _strength(len(c))}
        for c in clusters
    ]


def support_resistance(candles, window=3):
    """Calculate support and resistance levels from a set of candles."""
    if not candles:
        return {"support": [], "resistance": [], "current_price": None}

    last_candle = candles[-1]
    current_price = last_candle.get("close") or last_candle.get("high")

    highs, lows = find_swing_points(candles, window)

    resistances = cluster_levels(highs)
    supports = cluster_levels(lows)

    return {
        "support": [s for s in supports if s["level"] < current_price],
        "resistance": [r for r in resistances if r["level"] > current_price],
        "current_price": current_price,
    }


def _strength(touches):
    if touches >= 4:
        return "strong"
    if touches >= 2:
        return "moderate"
    return "weak"
