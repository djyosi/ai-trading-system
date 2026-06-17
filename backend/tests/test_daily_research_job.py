import json

import pytest

from app.jobs.daily_research import (
    DailyResearchSafetyError,
    build_daily_research_preflight,
    run_daily_research,
    write_daily_research_artifacts,
)


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


class FakeDailyProvider:
    def __init__(self):
        self.candle_calls = []
        self.news_calls = []

    async def get_daily_candles(self, ticker, start, end):
        self.candle_calls.append({"ticker": ticker, "start": start, "end": end})
        return [
            _candle(1, 100.0, 99.0, 99.5),
            _candle(2, 101.0, 99.5, 100.5),
            _candle(3, 102.0, 100.5, 101.5),
            _candle(4, 104.0, 101.0, 103.0),
            _candle(5, 106.0, 102.0, 105.0),
        ]

    async def get_news(self, ticker, start, end):
        self.news_calls.append({"ticker": ticker, "start": start, "end": end})
        return [
            {
                "ticker": ticker,
                "timestamp_ms": 2 * 86_400_000,
                "catalyst_type": "contract_win",
                "summary": "Company wins a new enterprise contract",
                "source": "fake",
            }
        ]


def _candle(index, high, low, close, volume=5_000_000):
    return {
        "timestamp_ms": index * 86_400_000,
        "open": close - 0.2,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "vwap": round((high + low + close) / 3, 2),
    }


@pytest.mark.asyncio
async def test_run_daily_research_requires_explicit_live_confirmation_for_provider_fetches():
    provider = FakeDailyProvider()

    with pytest.raises(DailyResearchSafetyError, match="explicit live research confirmation"):
        await run_daily_research(
            mode="live",
            market_data_provider=provider,
            confirm_live_data=False,
            run_date="2026-06-16",
            start="2026-01-02",
            end="2026-03-31",
            tickers=["AAPL"],
            universe_preset=None,
            include_news_catalysts=True,
        )

    assert provider.candle_calls == []
    assert provider.news_calls == []


@pytest.mark.asyncio
async def test_run_daily_research_live_mode_returns_sanitized_paper_safe_summary():
    provider = FakeDailyProvider()

    report = await run_daily_research(
        mode="live",
        market_data_provider=provider,
        confirm_live_data=True,
        run_date="2026-06-16",
        start="2026-01-02",
        end="2026-03-31",
        tickers=["AAPL"],
        universe_preset=None,
        include_news_catalysts=True,
        lookback_bars=3,
        horizon_bars=1,
        min_trades=1,
    )

    assert report["run_type"] == "daily_phase_3_research_live"
    assert report["mode"] == "live"
    assert report["orders_enabled"] is False
    assert report["live_data_enabled"] is True
    assert report["tickers_total"] == 1
    assert report["tickers_completed"] == 1
    assert report["news_catalysts_fetched"] == 1
    assert report["run_configuration"]["orders_enabled"] is False
    assert "paper_validation" in report
    assert "research_report" in report
    assert "results" not in report
    assert "items" not in report
    assert "raw_payload" not in json.dumps(report)
    assert provider.candle_calls == [{"ticker": "AAPL", "start": "2026-01-02", "end": "2026-03-31"}]
    assert provider.news_calls == [{"ticker": "AAPL", "start": "2026-01-02", "end": "2026-03-31"}]
