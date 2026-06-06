from app.catalysts.classifier import classify_catalyst, calculate_freshness


def test_classify_insider_director_purchase_is_bullish_strong():
    catalyst = classify_catalyst({"catalyst_type": "insider_director_purchase", "strength": "strong"})

    assert catalyst == {
        "catalyst_type": "insider_director_purchase",
        "signal": "bullish",
        "strength": "strong",
        "score": 90,
    }


def test_classify_insider_option_related_sale_is_neutral_weak():
    catalyst = classify_catalyst({"catalyst_type": "insider_option_related_sale"})

    assert catalyst["signal"] == "neutral"
    assert catalyst["strength"] == "weak"
    assert catalyst["score"] == 10


def test_classify_known_news_catalysts():
    assert classify_catalyst({"catalyst_type": "earnings_beat"})["score"] == 75
    assert classify_catalyst({"catalyst_type": "guidance_raise"})["score"] == 85
    assert classify_catalyst({"catalyst_type": "analyst_upgrade"})["score"] == 60
    assert classify_catalyst({"catalyst_type": "fda_approval"})["score"] == 90
    assert classify_catalyst({"catalyst_type": "merger_acquisition"})["score"] == 80
    assert classify_catalyst({"catalyst_type": "guidance_cut"})["signal"] == "bearish"


def test_unknown_catalyst_is_neutral_low_score():
    assert classify_catalyst({"catalyst_type": "unknown"}) == {
        "catalyst_type": "unknown",
        "signal": "neutral",
        "strength": "weak",
        "score": 0,
    }


def test_calculate_freshness_from_event_age_minutes():
    assert calculate_freshness(age_minutes=20) == "fresh"
    assert calculate_freshness(age_minutes=240) == "same_day"
    assert calculate_freshness(age_minutes=2_000) == "stale"
