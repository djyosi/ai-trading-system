from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.repositories.recommendations import RecommendationRepository


def _client_with_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def _recommendation(ticker, strategy="gap_and_go"):
    return {
        "ticker": ticker,
        "timeframe": "day_trade",
        "direction": "long",
        "status": "active_watch",
        "setup_score": 80,
        "confidence": "medium_high",
        "strategy": strategy,
        "entry_trigger": "breakout",
        "entry_zone": [10.0, 10.2],
        "stop_loss": 9.7,
        "targets": [10.8],
        "risk_reward": 2.0,
        "invalid_if": [],
        "reject_reasons": [],
        "warnings": [],
        "reason": "test",
        "inputs": {
            "features": {},
            "catalyst": {"catalyst_type": "earnings_beat"},
            "market_context": {"risk_context": "supportive"},
        },
    }


def test_performance_endpoint_returns_aggregate_learning_metrics():
    client, SessionLocal = _client_with_db()
    db = SessionLocal()
    repo = RecommendationRepository(db)
    winner = repo.save_recommendation(_recommendation("AAA"))
    loser = repo.save_recommendation(_recommendation("BBB"))
    repo.save_outcome(winner.id, {"status": "closed", "realized_r": 2.0, "target_hit": True})
    repo.save_outcome(loser.id, {"status": "closed", "realized_r": -1.0, "stop_hit": True})
    db.close()

    response = client.get("/api/performance")

    assert response.status_code == 200
    payload = response.json()
    assert payload["closed_total"] == 2
    assert payload["win_rate"] == 0.5
    assert payload["average_realized_r"] == 0.5
    assert payload["by_strategy"]["gap_and_go"]["expectancy_r"] == 0.5
    assert payload["by_score_band"]["70-84"]["closed_total"] == 2
    assert payload["by_score_band"]["70-84"]["expectancy_r"] == 0.5
    app.dependency_overrides.clear()
