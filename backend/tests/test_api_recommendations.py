from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.repositories.recommendations import RecommendationRepository


def _recommendation_payload(ticker="PAX", status="active_watch"):
    return {
        "ticker": ticker,
        "timeframe": "day_trade",
        "direction": "long",
        "status": status,
        "setup_score": 93,
        "confidence": "high",
        "strategy": "catalyst_momentum_gap_and_go",
        "strategy_segment": "catalyst_momentum_gap_and_go|analyst_upgrade",
        "research_tags": ["segment_edge_candidate", "market_context_edge_candidate"],
        "research_evidence": {
            "market_context_segment": "catalyst_momentum_gap_and_go|analyst_upgrade|supportive",
            "recommended_threshold": 60,
            "trade_count": 38,
            "win_rate": 0.45,
            "expectancy_r": 0.12,
        },
        "entry_trigger": "break_above_intraday_high_or_clean_vwap_hold",
        "entry_zone": [11.43, 11.67],
        "stop_loss": 11.09,
        "targets": [12.24, 12.75],
        "risk_reward": 1.5,
        "invalid_if": ["loses VWAP"],
        "reject_reasons": [],
        "warnings": [],
        "reason": "Strong bullish catalyst.",
        "inputs": {"features": {}, "catalyst": {}, "market_context": {}},
    }


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


def test_list_recommendations_endpoint_returns_latest_recommendations():
    client, SessionLocal = _client_with_db()
    db = SessionLocal()
    repo = RecommendationRepository(db)
    repo.save_recommendation(_recommendation_payload(ticker="AAPL"))
    repo.save_recommendation(_recommendation_payload(ticker="PAX"))
    db.close()

    response = client.get("/api/recommendations")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    assert payload["items"][0]["ticker"] == "PAX"
    assert payload["items"][0]["strategy_segment"] == "catalyst_momentum_gap_and_go|analyst_upgrade"
    assert payload["items"][0]["research_tags"] == ["segment_edge_candidate", "market_context_edge_candidate"]
    assert payload["items"][0]["research_evidence"]["market_context_segment"] == "catalyst_momentum_gap_and_go|analyst_upgrade|supportive"
    assert payload["items"][0]["rank_evidence"] == {
        "market_context_boost_eligible": True,
        "market_context_boost_status": "eligible",
        "market_context_segment": "catalyst_momentum_gap_and_go|analyst_upgrade|supportive",
        "recommended_threshold": 60,
        "win_rate": 0.45,
        "expectancy_r": 0.12,
        "trade_count": 38,
        "min_trade_count": 10,
    }
    assert payload["items"][0]["input_snapshot"] == {"features": {}, "catalyst": {}, "market_context": {}}
    app.dependency_overrides.clear()


def test_get_recommendation_endpoint_returns_single_record():
    client, SessionLocal = _client_with_db()
    db = SessionLocal()
    repo = RecommendationRepository(db)
    record = repo.save_recommendation(_recommendation_payload(ticker="PAX"))
    db.close()

    response = client.get(f"/api/recommendations/{record.id}")

    assert response.status_code == 200
    assert response.json()["ticker"] == "PAX"
    assert response.json()["strategy"] == "catalyst_momentum_gap_and_go"
    assert response.json()["strategy_segment"] == "catalyst_momentum_gap_and_go|analyst_upgrade"
    assert response.json()["research_evidence"]["expectancy_r"] == 0.12
    assert response.json()["rank_evidence"]["market_context_boost_status"] == "eligible"
    assert response.json()["rank_evidence"]["market_context_boost_eligible"] is True
    app.dependency_overrides.clear()


def test_get_recommendation_endpoint_returns_404_for_missing_record():
    client, _ = _client_with_db()

    response = client.get("/api/recommendations/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Recommendation not found"
    app.dependency_overrides.clear()
