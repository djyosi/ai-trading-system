from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.repositories.recommendations import RecommendationRepository


def _client_with_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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


def _recommendation(ticker, score, status="active_watch", with_research_evidence=True):
    research_tags = ["segment_edge_candidate", "market_context_edge_candidate"] if with_research_evidence else []
    research_evidence = {
        "market_context_segment": "gap_and_go|earnings_beat|supportive",
        "recommended_threshold": 60,
        "trade_count": 38,
        "win_rate": 0.45,
        "expectancy_r": 0.12,
    } if with_research_evidence else {}
    return {
        "ticker": ticker,
        "timeframe": "day_trade",
        "direction": "long",
        "status": status,
        "setup_score": score,
        "confidence": "high",
        "strategy": "gap_and_go",
        "strategy_segment": "gap_and_go|earnings_beat",
        "research_tags": research_tags,
        "research_evidence": research_evidence,
        "entry_trigger": "breakout",
        "entry_zone": [10.0, 10.2],
        "stop_loss": 9.5,
        "targets": [11.0],
        "risk_reward": 2.0,
        "invalid_if": [],
        "reject_reasons": [] if status != "no_trade" else ["weak_setup"],
        "warnings": [],
        "reason": "test",
        "inputs": {"features": {"relative_volume": 3.0}, "catalyst": {"catalyst_type": "earnings_beat"}, "market_context": {}},
    }


def test_dashboard_ranked_recommendations_returns_actionable_sorted_opportunities():
    client, SessionLocal = _client_with_db()
    db = SessionLocal()
    repo = RecommendationRepository(db)
    repo.save_recommendation(_recommendation("LOW", 62))
    repo.save_recommendation(_recommendation("SKIP", 95, status="no_trade"))
    repo.save_recommendation(_recommendation("HIGH", 91))
    db.close()

    response = client.get("/api/dashboard/ranked-recommendations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items_total"] == 2
    assert [item["ticker"] for item in payload["items"]] == ["HIGH", "LOW"]
    assert payload["items"][0]["rank"] == 1
    assert payload["items"][0]["setup_score"] == 91
    assert payload["items"][0]["strategy_segment"] == "gap_and_go|earnings_beat"
    assert payload["items"][0]["research_tags"] == ["segment_edge_candidate", "market_context_edge_candidate"]
    assert payload["items"][0]["research_evidence"]["market_context_segment"] == "gap_and_go|earnings_beat|supportive"
    assert payload["items"][0]["catalyst_type"] == "earnings_beat"
    app.dependency_overrides.clear()


def test_dashboard_ranking_uses_small_context_evidence_boost():
    client, SessionLocal = _client_with_db()
    db = SessionLocal()
    repo = RecommendationRepository(db)
    repo.save_recommendation(_recommendation("RAW_SCORE_ONLY", 90, with_research_evidence=False))
    repo.save_recommendation(_recommendation("EVIDENCE", 88, with_research_evidence=True))
    db.close()

    response = client.get("/api/dashboard/ranked-recommendations")

    assert response.status_code == 200
    payload = response.json()
    assert [item["ticker"] for item in payload["items"]] == ["EVIDENCE", "RAW_SCORE_ONLY"]
    assert payload["items"][0]["rank_score"] == 93
    assert payload["items"][1]["rank_score"] == 90
    app.dependency_overrides.clear()
