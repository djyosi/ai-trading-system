import json

from app.jobs.daily_research_status import latest_daily_research_status


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_latest_daily_research_status_returns_missing_when_no_artifacts_exist(tmp_path):
    status = latest_daily_research_status(output_dir=tmp_path)

    assert status == {
        "status": "missing",
        "latest_run_date": None,
        "mode": None,
        "orders_enabled": False,
        "live_data_enabled": False,
        "artifact_paths": None,
        "next_step": "run_daily_research_preflight",
    }


def test_latest_daily_research_status_selects_newest_preflight_artifact(tmp_path):
    _write_json(
        tmp_path / "daily-research-2026-06-16.json",
        {
            "run_date": "2026-06-16",
            "run_type": "daily_phase_3_research_preflight",
            "mode": "preflight",
            "orders_enabled": False,
            "live_data_enabled": False,
            "universe_preset": "liquid_research_100",
            "tickers_total": 100,
            "estimated_provider_calls": 203,
            "warnings": [],
            "next_step": "older",
            "raw_payload": {"must": "not leak"},
        },
    )
    _write_json(
        tmp_path / "daily-research-2026-06-17.json",
        {
            "run_date": "2026-06-17",
            "run_type": "daily_phase_3_research_preflight",
            "mode": "preflight",
            "orders_enabled": False,
            "live_data_enabled": False,
            "universe_preset": "liquid_research_500",
            "tickers_total": 500,
            "start": "2026-03-18",
            "end": "2026-06-16",
            "estimated_provider_calls": 1003,
            "warnings": ["large_provider_call_count"],
            "next_step": "review_preflight_then_enable_explicit_live_research_run",
            "items": [{"must": "not leak"}],
        },
    )

    status = latest_daily_research_status(output_dir=tmp_path)

    assert status == {
        "status": "available",
        "latest_run_date": "2026-06-17",
        "run_type": "daily_phase_3_research_preflight",
        "mode": "preflight",
        "orders_enabled": False,
        "live_data_enabled": False,
        "universe_preset": "liquid_research_500",
        "tickers_total": 500,
        "start": "2026-03-18",
        "end": "2026-06-16",
        "estimated_provider_calls": 1003,
        "warnings": ["large_provider_call_count"],
        "phase_3_readiness_status": None,
        "paper_validation_summary": None,
        "diagnostics_summary": None,
        "next_step": "review_preflight_then_enable_explicit_live_research_run",
        "artifact_paths": {
            "json": str(tmp_path / "daily-research-2026-06-17.json"),
            "markdown": str(tmp_path / "daily-research-2026-06-17.md"),
        },
    }
    assert "items" not in json.dumps(status)
    assert "raw_payload" not in json.dumps(status)


def test_latest_daily_research_status_summarizes_live_artifact_without_item_dump(tmp_path):
    _write_json(
        tmp_path / "daily-research-2026-06-17.json",
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
            "paper_validation": {
                "summary": {
                    "closed_count": 8,
                    "expectancy_r": -0.15,
                },
                "items": [{"must": "not leak"}],
            },
            "research_report": {
                "phase_3_readiness": {
                    "status": "needs_loss_driver_diagnostics",
                    "next_step": "diagnose_evidence_backed_loss_drivers_before_scaling",
                }
            },
            "diagnostics_summary": {
                "phase_3_readiness_status": "needs_loss_driver_diagnostics",
                "worst_loss_drivers": [{"segment": "analyst_upgrade", "expectancy_r": -1.0}],
            },
            "results": {"must": "not leak"},
            "next_step": "diagnose_evidence_backed_loss_drivers_before_scaling",
        },
    )

    status = latest_daily_research_status(output_dir=tmp_path)

    assert status["mode"] == "live"
    assert status["orders_enabled"] is False
    assert status["live_data_enabled"] is True
    assert status["tickers_completed"] == 24
    assert status["tickers_failed"] == 1
    assert status["news_catalysts_fetched"] == 321
    assert status["phase_3_readiness_status"] == "needs_loss_driver_diagnostics"
    assert status["paper_validation_summary"] == {"closed_count": 8, "expectancy_r": -0.15}
    assert status["diagnostics_summary"] == {
        "phase_3_readiness_status": "needs_loss_driver_diagnostics",
        "worst_loss_drivers": [{"segment": "analyst_upgrade", "expectancy_r": -1.0}],
    }
    assert "items" not in json.dumps(status)
    assert "results" not in json.dumps(status)
