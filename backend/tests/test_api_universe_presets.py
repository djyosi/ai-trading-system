from fastapi.testclient import TestClient

from app.main import app


def test_universe_presets_api_reports_counts_and_phase_3_default():
    client = TestClient(app)

    response = client.get("/api/backtests/universe-presets")

    assert response.status_code == 200
    payload = response.json()
    assert payload["phase_3_default_preset"] == "liquid_research_500"
    assert payload["phase_3_default_count"] == 500
    assert payload["broad_presets"] == [
        {"name": "liquid_research_25", "count": 25, "unique_count": 25, "first": "AAPL", "last": "XOM"},
        {"name": "liquid_research_50", "count": 50, "unique_count": 50, "first": "AAPL", "last": "DIA"},
        {"name": "liquid_research_100", "count": 100, "unique_count": 100, "first": "AAPL", "last": "ABNB"},
        {"name": "liquid_research_250", "count": 250, "unique_count": 250, "first": "AAPL", "last": "ELV"},
        {"name": "liquid_research_500", "count": 500, "unique_count": 500, "first": "AAPL", "last": "UNP"},
    ]
    assert any(item["name"] == "sector_semiconductors" and item["count"] == 12 for item in payload["sector_presets"])
