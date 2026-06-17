import json

from fastapi.testclient import TestClient

from app.api.routes.daily_research import get_daily_research_output_dir
from app.main import app


def test_latest_daily_research_api_returns_latest_sanitized_status(tmp_path):
    (tmp_path / "daily-research-2026-06-17.json").write_text(
        json.dumps(
            {
                "run_date": "2026-06-17",
                "run_type": "daily_phase_3_research_live",
                "mode": "live",
                "orders_enabled": False,
                "live_data_enabled": True,
                "universe_preset": "liquid_research_25",
                "tickers_total": 25,
                "tickers_completed": 24,
                "tickers_failed": 1,
                "news_catalysts_fetched": 321,
                "paper_validation": {"summary": {"closed_count": 8, "expectancy_r": -0.15}, "items": [1]},
                "research_report": {
                    "phase_3_readiness": {
                        "status": "needs_loss_driver_diagnostics",
                        "next_step": "diagnose_evidence_backed_loss_drivers_before_scaling",
                    }
                },
                "next_step": "diagnose_evidence_backed_loss_drivers_before_scaling",
                "results": {"must": "not leak"},
            }
        ),
        encoding="utf-8",
    )
    app.dependency_overrides[get_daily_research_output_dir] = lambda: tmp_path
    client = TestClient(app)

    try:
        response = client.get("/api/daily-research/latest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "available"
    assert payload["latest_run_date"] == "2026-06-17"
    assert payload["mode"] == "live"
    assert payload["orders_enabled"] is False
    assert payload["live_data_enabled"] is True
    assert payload["tickers_completed"] == 24
    assert payload["phase_3_readiness_status"] == "needs_loss_driver_diagnostics"
    assert payload["paper_validation_summary"] == {"closed_count": 8, "expectancy_r": -0.15}
    assert "items" not in json.dumps(payload)
    assert "results" not in json.dumps(payload)


def test_latest_daily_research_api_returns_missing_status_when_no_artifacts_exist(tmp_path):
    app.dependency_overrides[get_daily_research_output_dir] = lambda: tmp_path
    client = TestClient(app)

    try:
        response = client.get("/api/daily-research/latest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "missing",
        "latest_run_date": None,
        "mode": None,
        "orders_enabled": False,
        "live_data_enabled": False,
        "artifact_paths": None,
        "next_step": "run_daily_research_preflight",
    }
