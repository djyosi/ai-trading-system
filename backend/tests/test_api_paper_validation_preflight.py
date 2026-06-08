from fastapi.testclient import TestClient

from app.main import app


def test_paper_validation_research_preflight_estimates_provider_calls_without_running_data_fetches():
    client = TestClient(app)

    response = client.post(
        "/api/backtests/paper-validation-research/preflight",
        json={
            "start": "2026-01-01",
            "end": "2026-02-01",
            "include_news_catalysts": True,
            "include_market_context": True,
            "lookback_bars": 20,
            "horizon_bars": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "run_type": "phase_3_paper_validation_preflight",
        "universe_preset": "liquid_research_500",
        "tickers_total": 500,
        "start": "2026-01-01",
        "end": "2026-02-01",
        "market_data_candle_calls": 503,
        "news_catalyst_calls": 500,
        "estimated_provider_calls": 1003,
        "include_news_catalysts": True,
        "include_market_context": True,
        "orders_enabled": False,
        "warnings": ["large_provider_call_count"],
    }


def test_paper_validation_research_preflight_dedupes_custom_tickers_with_preset():
    client = TestClient(app)

    response = client.post(
        "/api/backtests/paper-validation-research/preflight",
        json={
            "tickers": ["aapl", "NEW1"],
            "universe_preset": "liquid_research_25",
            "start": "2026-01-01",
            "end": "2026-02-01",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe_preset"] == "liquid_research_25"
    assert payload["tickers_total"] == 26
    assert payload["market_data_candle_calls"] == 26
    assert payload["news_catalyst_calls"] == 0
    assert payload["estimated_provider_calls"] == 26
    assert payload["warnings"] == []
