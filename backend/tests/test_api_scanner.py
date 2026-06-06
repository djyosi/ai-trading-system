from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.scanner import get_scanner_service
from app.db.base import Base
from app.main import app


class FakeScannerService:
    async def scan(self, tickers):
        return [
            {
                "ticker": ticker,
                "status": "active_watch" if ticker == "PAX" else "no_trade",
                "setup_score": 91 if ticker == "PAX" else 0,
            }
            for ticker in tickers
        ]


def _client_with_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessionmaker(bind=engine)
    app.dependency_overrides[get_scanner_service] = lambda: FakeScannerService()
    return TestClient(app)


def test_scan_endpoint_returns_recommendations_for_requested_tickers():
    client = _client_with_db()

    response = client.post("/api/scan", json={"tickers": ["PAX", "THIN"]})

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"ticker": "PAX", "status": "active_watch", "setup_score": 91},
            {"ticker": "THIN", "status": "no_trade", "setup_score": 0},
        ]
    }
    app.dependency_overrides.clear()


def test_scan_endpoint_rejects_empty_ticker_list():
    client = _client_with_db()

    response = client.post("/api/scan", json={"tickers": []})

    assert response.status_code == 400
    assert response.json()["detail"] == "At least one ticker is required"
    app.dependency_overrides.clear()
