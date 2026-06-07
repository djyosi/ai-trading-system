from app.backtesting.walk_forward import run_walk_forward_replay


def _candle(index, open_price, high, low, close, volume=1_000_000):
    return {
        "timestamp_ms": index * 86_400_000,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "vwap": round((high + low + close) / 3, 2),
    }


def _bullish_catalyst(timestamp_ms):
    return {
        "type": "earnings_beat",
        "headline": "Company reports earnings beat and raises guidance",
        "summary": "Earnings beat and raised guidance",
        "timestamp_ms": timestamp_ms,
    }


def test_walk_forward_replay_creates_recommendations_and_labels_future_outcomes():
    candles = [
        _candle(1, 9.8, 10.0, 9.6, 9.9, volume=800_000),
        _candle(2, 9.9, 10.2, 9.7, 10.0, volume=900_000),
        _candle(3, 10.0, 10.4, 9.8, 10.1, volume=950_000),
        _candle(4, 10.9, 11.8, 10.7, 11.5, volume=3_200_000),
        _candle(5, 11.6, 12.8, 11.4, 12.4, volume=2_400_000),
        _candle(6, 12.4, 13.2, 12.1, 13.0, volume=2_000_000),
    ]

    result = run_walk_forward_replay(
        ticker="PAX",
        candles=candles,
        catalysts=[_bullish_catalyst(candles[3]["timestamp_ms"])],
        market_context={"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
        lookback_bars=3,
        horizon_bars=2,
    )

    assert result["ticker"] == "PAX"
    assert result["evaluated_bars"] == 3
    assert len(result["items"]) == 3
    first = result["items"][0]
    assert first["recommendation"]["ticker"] == "PAX"
    assert first["recommendation"]["inputs"]["features"]["previous_close"] == 10.1
    assert first["recommendation"]["inputs"]["catalyst"]["catalyst_type"] == "earnings_beat"
    assert first["outcome"]["status"] == "closed"
    assert first["outcome"]["target_hit"] is True
    assert first["outcome"]["bars_to_target"] == 1
    assert result["summary"]["closed_total"] >= 1


def test_walk_forward_replay_prevents_lookahead_in_features_and_catalysts():
    candles = [
        _candle(1, 9.8, 10.0, 9.6, 9.9),
        _candle(2, 9.9, 10.2, 9.7, 10.0),
        _candle(3, 10.0, 10.4, 9.8, 10.1),
        _candle(4, 10.9, 11.8, 10.7, 11.5, volume=3_200_000),
        _candle(5, 11.6, 99.0, 11.4, 12.4, volume=2_400_000),
    ]
    visible_catalyst = _bullish_catalyst(candles[3]["timestamp_ms"])
    future_catalyst = {
        "type": "guidance_raise",
        "headline": "Company raises guidance after the replay decision bar",
        "summary": "Future guidance raise",
        "timestamp_ms": candles[4]["timestamp_ms"],
    }

    result = run_walk_forward_replay(
        ticker="PAX",
        candles=candles,
        catalysts=[visible_catalyst, future_catalyst],
        market_context={"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
        lookback_bars=3,
        horizon_bars=1,
    )

    first = result["items"][0]
    features = first["recommendation"]["inputs"]["features"]
    assert features["prior_high"] == 10.4
    assert features["prior_high"] != 99.0
    assert first["recommendation"]["inputs"]["catalyst"]["catalyst_type"] == "earnings_beat"
    assert first["recommendation"]["inputs"]["catalyst"]["catalyst_type"] != "guidance_raise"
    assert first["outcome"]["target_hit"] is True


def test_walk_forward_replay_excludes_stale_catalysts_outside_freshness_window():
    candles = [
        _candle(1, 9.8, 10.0, 9.6, 9.9),
        _candle(2, 9.9, 10.2, 9.7, 10.0),
        _candle(3, 10.0, 10.4, 9.8, 10.1),
        _candle(4, 10.9, 11.8, 10.7, 11.5, volume=3_200_000),
        _candle(5, 11.6, 12.8, 11.4, 12.4, volume=2_400_000),
    ]
    stale_catalyst = _bullish_catalyst(candles[1]["timestamp_ms"])

    result = run_walk_forward_replay(
        ticker="PAX",
        candles=candles,
        catalysts=[stale_catalyst],
        market_context={"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
        lookback_bars=3,
        horizon_bars=1,
        catalyst_max_age_minutes=60,
    )

    first = result["items"][0]
    assert first["recommendation"]["inputs"]["catalyst"]["catalyst_type"] == "unknown"
    assert first["recommendation"]["inputs"]["catalyst"]["score"] == 0


def test_walk_forward_replay_can_use_lower_research_actionable_threshold():
    candles = [
        _candle(1, 209.0, 211.0, 208.0, 210.0),
        _candle(2, 210.0, 212.0, 209.0, 211.0),
        _candle(3, 211.0, 213.0, 210.0, 212.0),
        _candle(4, 212.5, 214.0, 211.5, 213.0),
        _candle(5, 213.0, 216.5, 212.0, 216.0),
    ]

    default_result = run_walk_forward_replay(
        ticker="AAPL",
        candles=candles,
        catalysts=[],
        market_context={"risk_context": "supportive"},
        lookback_bars=3,
        horizon_bars=1,
    )
    research_result = run_walk_forward_replay(
        ticker="AAPL",
        candles=candles,
        catalysts=[],
        market_context={"risk_context": "supportive"},
        lookback_bars=3,
        horizon_bars=1,
        actionable_score_threshold=30,
    )

    assert default_result["items"][0]["recommendation"]["status"] == "no_trade"
    assert research_result["items"][0]["recommendation"]["status"] == "active_watch"


def test_walk_forward_replay_can_persist_recommendations_and_outcomes():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base
    from app.repositories.recommendations import RecommendationRepository

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    repo = RecommendationRepository(sessionmaker(bind=engine)())
    candles = [
        _candle(1, 9.8, 10.0, 9.6, 9.9),
        _candle(2, 9.9, 10.2, 9.7, 10.0),
        _candle(3, 10.0, 10.4, 9.8, 10.1),
        _candle(4, 10.9, 11.8, 10.7, 11.5, volume=3_200_000),
        _candle(5, 11.6, 12.8, 11.4, 12.4, volume=2_400_000),
    ]

    result = run_walk_forward_replay(
        ticker="PAX",
        candles=candles,
        catalysts=[_bullish_catalyst(candles[3]["timestamp_ms"])],
        market_context={"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
        lookback_bars=3,
        horizon_bars=1,
        recommendation_repository=repo,
    )

    assert result["persisted_recommendations"] == 2
    records = repo.list_recommendations()
    assert len(records) == 2
    assert records[0].outcome is not None
