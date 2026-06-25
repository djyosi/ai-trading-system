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
        "weight": 3,  # SIM: 56.1% WR, +1.66% avg  ← BEST
    },
    "rsi_oversold": {
        "name": "RSI Oversold",
        "description": "RSI below 30, near support level",
        "conditions": [
            "rsi_14 < 30",
            "close > sma_50",
        ],
        "min_candles": 55,
        "weight": 2,  # SIM: 53.8% WR, +0.94% avg
    },
    "volume_support": {
        "name": "Volume Support Bounce",
        "description": "High volume bounce off support level",
        "conditions": [
            "volume > 2.0 * avg_volume_20",
            "close >= lower_band",
            "close > low_of_5",
        ],
        "min_candles": 25,
        "weight": 2,  # SIM: 50.0% WR, +1.01% avg
    },
    "golden_cross": {
        "name": "Golden Cross (SMA 50/200)",
        "description": "50 SMA crosses above 200 SMA with confirmation",
        "conditions": [
            "sma_50 > sma_200",
            "sma_50_1d <= sma_200_1d",
            "close > sma_50",
        ],
        "min_candles": 210,
        "weight": 2,  # Rare but strong signal
    },
    "bull_flag": {
        "name": "Bull Flag Breakout",
        "description": "Sharp move up followed by consolidation, ready to break",
        "conditions": [
            "bull_flag_detected",
            "volume > 1.5 * avg_volume_20",
        ],
        "min_candles": 25,
        "weight": 2,
    },
    "macd_crossover": {
        "name": "MACD Crossover",
        "description": "MACD line crosses above signal line (momentum shift)",
        "conditions": [
            "macd > signal",
            "macd_1d <= signal_1d",
        ],
        "min_candles": 30,
        "weight": 1,  # SIM: 49.3% WR, -0.45% avg  ← LOSING
    },
    "sma_20_50_bullish": {
        "name": "SMA 20/50 Bullish",
        "description": "SMA 20 above SMA 50 + price above both (short-term uptrend)",
        "conditions": [
            "sma_20 > sma_50",
            "close > sma_20",
        ],
        "min_candles": 55,
        "weight": 1,  # SIM: 48.8% WR, +0.15% avg ← random
    },
    "oversold_bollinger": {
        "name": "Oversold Bollinger Combo",
        "description": "RSI oversold AND touching lower band — strongest bounce signal",
        "conditions": [
            "rsi_14 < 35",
            "close <= lower_band",
            "volume > avg_volume_20",
        ],
        "min_candles": 25,
        "weight": 1,  # SIM: 50.0% WR, +0.33% avg
    },
    "high_volume_spike": {
        "name": "High Volume Spike",
        "description": "Volume more than 3x average — unusual activity",
        "conditions": [
            "volume > 3.0 * avg_volume_20",
        ],
        "min_candles": 25,
        "weight": 2,  # SIM: 66.7% WR, +11.67% avg (small sample)
    },
    "bullish_engulfing": {
        "name": "Bullish Engulfing",
        "description": "Bullish engulfing candle pattern (strong reversal signal)",
        "conditions": [
            "bullish_engulfing_detected",
            "volume > avg_volume_20",
        ],
        "min_candles": 25,
        "weight": 2,
    },
    "three_up_days": {
        "name": "3 Green Days",
        "description": "Three consecutive up days with increasing volume",
        "conditions": [
            "up_days_3",
            "volume_rising_3",
        ],
        "min_candles": 25,
        "weight": 1,
    },
    "bollinger_squeeze": {
        "name": "Bollinger Squeeze",
        "description": "Bollinger bands tightening — potential breakout soon",
        "conditions": [
            "band_width_pct < 0.05",
            "band_width_10d_ago > 0.08",
        ],
        "min_candles": 30,
        "weight": 1,  # SIM: 44.0% WR, -1.22% avg ← LOSING
    },
    "support_bounce": {
        "name": "Support Bounce",
        "description": "Near recent low + RSI turning up + volume confirmation",
        "conditions": [
            "close <= low_of_20 * 1.05",
            "rsi_14 > rsi_14_3d_ago",
            "volume > avg_volume_20",
        ],
        "min_candles": 30,
        "weight": 2,
    },
    "above_sma_50": {
        "name": "Above SMA 50 with Volume",
        "description": "Trading above 50-day MA with above-average volume",
        "conditions": [
            "close > sma_50",
            "volume > 1.5 * avg_volume_20",
        ],
        "min_candles": 55,
        "weight": 2,  # SIM: 50.8% WR, +0.76% avg
    },
}
