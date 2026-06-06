from app.features.market_context import classify_etf_trend, summarize_market_context


def test_classify_etf_trend_up_when_price_above_moving_average_and_positive_slope():
    candles = [
        {"close": 100},
        {"close": 101},
        {"close": 102},
        {"close": 103},
        {"close": 104},
    ]

    assert classify_etf_trend(candles, lookback=5) == "up"


def test_classify_etf_trend_down_when_price_below_moving_average_and_negative_slope():
    candles = [
        {"close": 104},
        {"close": 103},
        {"close": 102},
        {"close": 101},
        {"close": 100},
    ]

    assert classify_etf_trend(candles, lookback=5) == "down"


def test_classify_etf_trend_neutral_for_flat_or_insufficient_data():
    assert classify_etf_trend([{"close": 100}, {"close": 100}], lookback=5) == "neutral"
    assert classify_etf_trend([], lookback=5) == "neutral"


def test_summarize_market_context_supportive_when_spy_and_qqq_are_up():
    context = summarize_market_context(
        {
            "SPY": [{"close": 100}, {"close": 101}, {"close": 102}, {"close": 103}, {"close": 104}],
            "QQQ": [{"close": 200}, {"close": 202}, {"close": 204}, {"close": 206}, {"close": 208}],
            "IWM": [{"close": 190}, {"close": 190}, {"close": 190}, {"close": 190}, {"close": 190}],
        }
    )

    assert context == {
        "spy_trend": "up",
        "qqq_trend": "up",
        "iwm_trend": "neutral",
        "risk_context": "supportive",
    }


def test_summarize_market_context_risk_off_when_spy_and_qqq_are_down():
    context = summarize_market_context(
        {
            "SPY": [{"close": 104}, {"close": 103}, {"close": 102}, {"close": 101}, {"close": 100}],
            "QQQ": [{"close": 208}, {"close": 206}, {"close": 204}, {"close": 202}, {"close": 200}],
            "IWM": [{"close": 190}, {"close": 189}, {"close": 188}, {"close": 187}, {"close": 186}],
        }
    )

    assert context["risk_context"] == "risk_off"
    assert context["spy_trend"] == "down"
    assert context["qqq_trend"] == "down"


def test_summarize_market_context_mixed_otherwise():
    context = summarize_market_context(
        {
            "SPY": [{"close": 100}, {"close": 101}, {"close": 102}, {"close": 103}, {"close": 104}],
            "QQQ": [{"close": 208}, {"close": 206}, {"close": 204}, {"close": 202}, {"close": 200}],
            "IWM": [],
        }
    )

    assert context == {
        "spy_trend": "up",
        "qqq_trend": "down",
        "iwm_trend": "neutral",
        "risk_context": "mixed",
    }
