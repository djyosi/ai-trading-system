import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_technicals_endpoint_returns_analysis_for_ticker(client):
    """GET /api/technicals/AAPL should return S/R, channel, volume, entry signal."""
    response = client.get("/api/technicals/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert "signal" in data
    assert "support_levels" in data
    assert "resistance_levels" in data
    assert "channel" in data
    assert "volume_trend" in data
    assert "candle_pattern" in data


def test_technicals_endpoint_returns_404_for_empty_ticker(client):
    response = client.get("/api/technicals/")
    assert response.status_code in (404, 405)


def test_technicals_endpoint_includes_security_checks(client):
    """Verify safety fields are present."""
    response = client.get("/api/technicals/AAPL")
    data = response.json()
    assert "orders_enabled" in data
    assert data["orders_enabled"] is False
    assert "data_source" in data
