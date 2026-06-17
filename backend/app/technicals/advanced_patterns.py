PATTERN_DOUBLE_TOP = "double_top"
PATTERN_DOUBLE_BOTTOM = "double_bottom"
PATTERN_HS_TOP = "head_and_shoulders_top"
PATTERN_HS_BOTTOM = "head_and_shoulders_bottom"
PATTERN_BULL_FLAG = "bull_flag"
PATTERN_BEAR_FLAG = "bear_flag"

PCT_TOLERANCE = 0.03  # 3%


def _similar(a, b):
    """Check if two prices are within PCT_TOLERANCE of each other."""
    return abs(a - b) / max(a, b, 1) <= PCT_TOLERANCE


def detect_head_shoulders(candles, window=2):
    """Head & shoulders: 3 peaks, middle highest. Uses direct scan, not swing points."""
    if len(candles) < 7:
        return {"detected": False, "pattern": PATTERN_HS_TOP}

    for i in range(2, len(candles) - 2):
        left = candles[i - 2].get("high", 0)
        head = candles[i].get("high", 0)
        right = candles[i + 2].get("high", 0)
        if head > left and head > right and _similar(left, right):
            neckline = min(candles[i - 2].get("low", 0), candles[i].get("low", 0), candles[i + 2].get("low", 0))
            return {
                "detected": True, "pattern": PATTERN_HS_TOP, "direction": "bearish",
                "target": head, "neckline": neckline, "strength": "strong",
            }
    return {"detected": False, "pattern": PATTERN_HS_TOP}


def detect_double_top(candles, window=2):
    """Double top: check swing pairs directly."""
    highs = [c.get("high") for c in candles if c.get("high") is not None]
    for i in range(len(highs) - 3):
        for j in range(i + 2, len(highs) - 1):
            if _similar(highs[i], highs[j]) and abs(highs[i] - highs[j]) > 0.01:
                return {
                    "detected": True, "pattern": PATTERN_DOUBLE_TOP, "direction": "bearish",
                    "target": highs[i], "strength": "moderate",
                }
    return {"detected": False, "pattern": PATTERN_DOUBLE_TOP}


def detect_double_bottom(candles, window=2):
    """Double bottom: check trough pairs directly."""
    lows = [c.get("low") for c in candles if c.get("low") is not None]
    for i in range(len(lows) - 3):
        for j in range(i + 2, len(lows) - 1):
            if _similar(lows[i], lows[j]) and abs(lows[i] - lows[j]) > 0.01:
                return {
                    "detected": True, "pattern": PATTERN_DOUBLE_BOTTOM, "direction": "bullish",
                    "target": lows[i], "strength": "moderate",
                }
    return {"detected": False, "pattern": PATTERN_DOUBLE_BOTTOM}


def detect_flag(candles, window=5):
    """Flag: sharp move (pole) + consolidation (flag)."""
    if len(candles) < window * 2:
        return {"detected": False, "pattern": PATTERN_BULL_FLAG}

    pole = candles[:window]
    flag = candles[window:window * 2]

    pole_start = pole[0].get("close", 0)
    pole_end = pole[-1].get("close", pole_start)
    pole_move = (pole_end - pole_start) / max(pole_start, 1)

    flag_start = flag[0].get("close", 0)
    flag_end = flag[-1].get("close", flag_start)
    flag_move = (flag_end - flag_start) / max(flag_start, 1)

    if abs(pole_move) < 0.05:  # need at least 5% move
        return {"detected": False, "pattern": PATTERN_BULL_FLAG}

    if pole_move > 0 and abs(flag_move) < abs(pole_move) * 0.5:
        return {"detected": True, "pattern": PATTERN_BULL_FLAG, "direction": "bullish", "pole_move": round(pole_move, 2), "strength": "moderate"}
    if pole_move < 0 and abs(flag_move) < abs(pole_move) * 0.5:
        return {"detected": True, "pattern": PATTERN_BEAR_FLAG, "direction": "bearish", "pole_move": round(pole_move, 2), "strength": "moderate"}

    return {"detected": False, "pattern": PATTERN_BULL_FLAG}


def analyze_advanced_patterns(candles):
    """Run all advanced pattern detectors. Returns list of results + best pattern."""
    results = [
        detect_double_top(candles),
        detect_double_bottom(candles),
        detect_head_shoulders(candles),
        detect_flag(candles),
    ]
    detected = [r for r in results if r["detected"]]
    best = max(detected, key=lambda r: {"weak": 1, "moderate": 2, "strong": 3}.get(r.get("strength", "weak"), 0)) if detected else {"detected": False, "pattern": "none"}
    results.append({"pattern": "best_advanced", "detected": best["detected"], "result": best})
    return results
