from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.outcome import OutcomeRecord
from app.models.recommendation import RecommendationRecord
from app.repositories.recommendations import RecommendationRepository


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _recommendation_payload():
    return {
        "ticker": "PAX",
        "timeframe": "day_trade",
        "direction": "long",
        "status": "active_watch",
        "setup_score": 93,
        "confidence": "high",
        "strategy": "catalyst_momentum_gap_and_go",
        "entry_trigger": "break_above_intraday_high_or_clean_vwap_hold",
        "entry_zone": [11.43, 11.67],
        "stop_loss": 11.09,
        "targets": [12.24, 12.75],
        "risk_reward": 1.5,
        "invalid_if": ["loses VWAP", "relative volume fades"],
        "reject_reasons": [],
        "warnings": [],
        "reason": "Strong bullish catalyst; relative volume 3.2x.",
        "inputs": {
            "features": {"gap_percent": 7.5, "relative_volume": 3.2, "liquidity_score": 92},
            "catalyst": {"catalyst_type": "insider_director_purchase", "score": 90},
            "market_context": {"risk_context": "supportive"},
        },
    }


def test_recommendation_record_preserves_strategy_risk_and_input_snapshots():
    db = _session()
    repo = RecommendationRepository(db)
    created_at = datetime(2026, 6, 6, 14, 30, tzinfo=timezone.utc)

    record = repo.save_recommendation(_recommendation_payload(), created_at=created_at)

    assert record.id is not None
    assert record.ticker == "PAX"
    assert record.status == "active_watch"
    assert record.setup_score == 93
    assert record.entry_zone == [11.43, 11.67]
    assert record.targets == [12.24, 12.75]
    assert record.input_snapshot["features"]["relative_volume"] == 3.2
    assert record.created_at.replace(tzinfo=timezone.utc) == created_at


def test_recommendation_repository_lists_latest_records_first():
    db = _session()
    repo = RecommendationRepository(db)

    first = _recommendation_payload()
    first["ticker"] = "AAPL"
    second = _recommendation_payload()
    second["ticker"] = "PAX"

    repo.save_recommendation(first, created_at=datetime(2026, 6, 6, 14, 0, tzinfo=timezone.utc))
    repo.save_recommendation(second, created_at=datetime(2026, 6, 6, 15, 0, tzinfo=timezone.utc))

    records = repo.list_recommendations(limit=10)

    assert [record.ticker for record in records] == ["PAX", "AAPL"]


def test_outcome_record_links_to_recommendation_for_learning_loop():
    db = _session()
    repo = RecommendationRepository(db)
    recommendation = repo.save_recommendation(_recommendation_payload())

    outcome = repo.save_outcome(
        recommendation_id=recommendation.id,
        outcome={
            "status": "closed",
            "max_favorable_excursion_r": 2.1,
            "max_adverse_excursion_r": -0.4,
            "realized_r": 1.5,
            "target_hit": True,
            "stop_hit": False,
            "bars_to_target": 12,
        },
    )

    loaded = db.query(OutcomeRecord).filter_by(recommendation_id=recommendation.id).one()
    assert outcome.id == loaded.id
    assert loaded.recommendation_id == recommendation.id
    assert loaded.realized_r == 1.5
    assert loaded.target_hit is True
    assert loaded.recommendation.ticker == "PAX"


def test_models_expose_expected_table_names_for_future_migrations():
    assert RecommendationRecord.__tablename__ == "recommendations"
    assert OutcomeRecord.__tablename__ == "outcomes"
