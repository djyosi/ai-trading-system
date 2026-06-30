import json

import pytest


@pytest.mark.asyncio
async def test_daily_scan_does_not_create_local_trades_by_default(monkeypatch, tmp_path, capsys):
    from app.ta_screener import daily_run

    class DummyResponse:
        status_code = 200

        def json(self):
            return {"results": []}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *args, **kwargs):
            return DummyResponse()

    async def fake_update_open_trades():
        return {"open": 0, "closed": 0, "wins": 0, "losses": 0}

    async def no_enrichment(client, recommendations, api_key, scan_date=None, limit=50):
        return recommendations

    monkeypatch.setattr(daily_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(daily_run, "OUTPUT_DIR", tmp_path / "scans")
    monkeypatch.setattr(daily_run, "AsyncClient", DummyClient)
    monkeypatch.setattr(daily_run, "update_open_trades", fake_update_open_trades)
    monkeypatch.setattr(daily_run, "enrich_recommendations", no_enrichment)
    monkeypatch.setattr(daily_run.settings, "ta_local_portfolio_enabled", False)

    (tmp_path / "backend" / "tmp").mkdir(parents=True)
    (tmp_path / "backend" / "tmp" / "research_tickers.json").write_text(json.dumps([]))

    result = await daily_run.run_daily_scan()
    stdout = capsys.readouterr().out

    assert result["top_recommendations"] == []
    assert "Local trades added: 0 (disabled; IBKR paper execution is source of truth)" in stdout
    assert (tmp_path / "scans" / f"scan-{result['scan_date']}.json").exists()
