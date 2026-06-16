import json

from app.jobs.daily_research import build_daily_research_preflight, write_daily_research_artifacts


def test_build_daily_research_preflight_defaults_to_paper_safe_phase_3_run():
    report = build_daily_research_preflight(
        run_date="2026-06-16",
        start="2026-01-02",
        end="2026-03-31",
        include_news_catalysts=True,
        include_market_context=True,
    )

    assert report == {
        "run_type": "daily_phase_3_research_preflight",
        "run_date": "2026-06-16",
        "orders_enabled": False,
        "live_data_enabled": False,
        "mode": "preflight",
        "universe_preset": "liquid_research_500",
        "tickers_total": 500,
        "start": "2026-01-02",
        "end": "2026-03-31",
        "market_data_candle_calls": 503,
        "news_catalyst_calls": 500,
        "estimated_provider_calls": 1003,
        "include_news_catalysts": True,
        "include_market_context": True,
        "actionable_score_threshold": 30,
        "min_trades": 5,
        "warnings": ["large_provider_call_count"],
        "next_step": "review_preflight_then_enable_explicit_live_research_run",
    }


def test_write_daily_research_artifacts_saves_sanitized_markdown_and_json(tmp_path):
    report = build_daily_research_preflight(
        run_date="2026-06-16",
        start="2026-01-02",
        end="2026-03-31",
        universe_preset="liquid_research_25",
    )

    artifact = write_daily_research_artifacts(report, output_dir=tmp_path)

    assert artifact["markdown_path"].endswith("daily-research-2026-06-16.md")
    assert artifact["json_path"].endswith("daily-research-2026-06-16.json")
    markdown = (tmp_path / "daily-research-2026-06-16.md").read_text()
    assert "# Daily AI Trading Research Preflight — 2026-06-16" in markdown
    assert "orders_enabled: false" in markdown
    assert "live_data_enabled: false" in markdown
    assert "universe_preset: liquid_research_25" in markdown
    assert "estimated_provider_calls: 25" in markdown
    payload = json.loads((tmp_path / "daily-research-2026-06-16.json").read_text())
    assert payload["orders_enabled"] is False
    assert payload["live_data_enabled"] is False
    assert "items" not in payload
    assert "raw_payload" not in payload
