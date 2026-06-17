from app.features.chart_patterns import classify_candle_pattern, classify_multi_candle_pattern
from app.technicals.advanced_patterns import analyze_advanced_patterns
from app.technicals.support_resistance import support_resistance
from app.technicals.channels import detect_channel, CHANNEL_UP, CHANNEL_DOWN
from app.technicals.volume import volume_trend, volume_divergence, TREND_SPIKE, DIVERGENCE_BULLISH, DIVERGENCE_BEARISH

SIGNAL_STRONG_BUY = "strong_buy"
SIGNAL_BUY = "buy"
SIGNAL_HOLD = "hold"
SIGNAL_SELL = "sell"
SIGNAL_STRONG_SELL = "strong_sell"


def analyze_technical(ticker, candles):
    """Full technical analysis of a single instrument.

    Returns a unified signal combining:
    - Support/Resistance levels
    - Channel trend (rising/falling/sideways)
    - Volume trend + divergence
    - Candle pattern (single + multi)
    - Entry recommendation
    """
    if not candles or len(candles) < 10:
        return {"ticker": ticker, "signal": SIGNAL_HOLD, "confidence": "low", "reasons": ["insufficient_data"]}

    sr = support_resistance(candles, window=3)
    channel = detect_channel(candles)
    vol_trend = volume_trend(candles)
    divergence = volume_divergence(candles)
    last_candle = candles[-1]
    pattern = classify_candle_pattern(last_candle)
    multi_pattern = classify_multi_candle_pattern(candles[-2], candles[-1]) if len(candles) >= 2 else {}
    adv_patterns = analyze_advanced_patterns(candles)
    best_adv = next((r["result"] for r in adv_patterns if r.get("detected") and r["pattern"] == "best_advanced"), {})

    reasons = []
    score = 0  # positive = bullish, negative = bearish

    # Channel analysis
    if channel["type"] == CHANNEL_UP:
        score += 2
        reasons.append(f"rising_channel (slope={channel['slope']})")
    elif channel["type"] == CHANNEL_DOWN:
        score -= 2
        reasons.append(f"falling_channel (slope={channel['slope']})")

    # S/R proximity
    current_price = sr.get("current_price")
    support_levels = sr.get("support", [])
    resistance_levels = sr.get("resistance", [])

    if support_levels and current_price:
        nearest_support = max(s["level"] for s in support_levels)
        dist_to_support = (current_price - nearest_support) / current_price * 100
        if dist_to_support < 2:
            score += 1
            reasons.append(f"near_support ({nearest_support})")

    if resistance_levels and current_price:
        nearest_resistance = min(r["level"] for r in resistance_levels)
        dist_to_resistance = (nearest_resistance - current_price) / current_price * 100
        if dist_to_resistance < 2:
            score -= 1
            reasons.append(f"near_resistance ({nearest_resistance})")

    # Volume
    if vol_trend == TREND_SPIKE:
        score += 1 if score >= 0 else -1
        reasons.append("volume_spike")

    if divergence == DIVERGENCE_BULLISH:
        score += 2
        reasons.append("bullish_divergence")
    elif divergence == DIVERGENCE_BEARISH:
        score -= 2
        reasons.append("bearish_divergence")

    # Advanced patterns (double top/bottom, H&S, flags)
    if best_adv.get("detected"):
        if best_adv.get("direction") == "bullish":
            score += 2
            reasons.append(f"{best_adv.get('pattern')}")
        elif best_adv.get("direction") == "bearish":
            score -= 2
            reasons.append(f"{best_adv.get('pattern')}")

    # Candle patterns
    pat = pattern if pattern["pattern"] != "none" else multi_pattern
    if pat:
        if pat.get("direction") == "bullish" and pat.get("pattern") != "none":
            score += 1
            reasons.append(f"{pat['pattern']}_{pat['direction']}")
        elif pat.get("direction") == "bearish" and pat.get("pattern") != "none":
            score -= 1
            reasons.append(f"{pat['pattern']}_{pat['direction']}")

    # Final signal
    if score >= 4:
        signal = SIGNAL_STRONG_BUY
    elif score >= 2:
        signal = SIGNAL_BUY
    elif score <= -4:
        signal = SIGNAL_STRONG_SELL
    elif score <= -2:
        signal = SIGNAL_SELL
    else:
        signal = SIGNAL_HOLD

    return {
        "ticker": ticker,
        "signal": signal,
        "score": score,
        "confidence": "high" if abs(score) >= 4 else "medium" if abs(score) >= 2 else "low",
        "reasons": reasons,
        "current_price": current_price,
        "support_levels": support_levels,
        "resistance_levels": resistance_levels,
        "channel": channel,
        "volume_trend": vol_trend,
        "volume_divergence": divergence,
        "candle_pattern": pat,
    }
