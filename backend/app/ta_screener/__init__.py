"""
Standalone Technical Screener — not tied to the trading system.

Usage:
    from app.ta_screener.scanner import run_screen
    results = await run_screen(["AAPL", "NVDA"], "bollinger_bounce")
"""

SCREENS = {
    "bollinger_bounce": {
        "name": "Bollinger Bounce",
        "description": "Price touches or breaks below lower Bollinger Band with high volume",
        "conditions": [
            "close <= lower_band",
            "volume > 1.3 * avg_volume_20",
        ],
        "min_candles": 25,
    },
    "rsi_oversold": {
        "name": "RSI Oversold",
        "description": "RSI below 30, near support level",
        "conditions": [
            "rsi_14 < 30",
            "close > sma_50",  # still in uptrend on higher timeframe
        ],
        "min_candles": 55,
    },
    "volume_support": {
        "name": "Volume Support Bounce",
        "description": "High volume bounce off support level",
        "conditions": [
            "volume > 2.0 * avg_volume_20",
            "close >= lower_band",  # not crashing through
            "close > low_of_5",  # bouncing off intra-period low
        ],
        "min_candles": 25,
    },
    "golden_cross": {
        "name": "Golden Cross (SMA 50/200)",
        "description": "50 SMA crosses above 200 SMA with confirmation",
        "conditions": [
            "sma_50 > sma_200",
            "sma_50_1d <= sma_200_1d",  # just crossed today
            "close > sma_50",
        ],
        "min_candles": 210,
    },
    "bull_flag": {
        "name": "Bull Flag Breakout",
        "description": "Sharp move up followed by consolidation, ready to break",
        "conditions": [
            "bull_flag_detected",
            "volume > 1.5 * avg_volume_20",
        ],
        "min_candles": 25,
    },
}
