from datetime import datetime, timezone

import pytest

from app.ta_screener.market_intel import (
    catalog_news,
    combine_intelligence,
    enrich_recommendations,
    score_snapshot,
)


def test_catalog_news_records_fresh_bullish_catalysts_without_scoring():
    result = catalog_news(
        [
            {
                "title": "ACME raises guidance after earnings beat",
                "description": "Management raised full-year revenue guidance.",
                "published_utc": "2026-06-29T12:00:00Z",
                "publisher": {"name": "Newswire"},
            }
        ],
        now=datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc),
    )

    assert result["news_score"] == 0
    assert result["catalog_only"] is True
    assert result["catalysts"][0]["type"] == "earnings_beat"
    assert result["catalysts"][0]["catalog_only"] is True
    assert result["risk_flags"] == []


def test_catalog_news_flags_bearish_catalysts_without_penalizing_score():
    result = catalog_news(
        [
            {
                "title": "ACME cuts guidance after earnings miss",
                "published_utc": "2026-06-29T12:00:00Z",
            }
        ],
        now=datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc),
    )

    assert result["news_score"] == 0
    assert "earnings_miss" in result["risk_flags"]


def test_score_snapshot_uses_gap_liquidity_and_spread():
    result = score_snapshot(
        {
            "day": {"c": 103.0, "v": 6_000_000},
            "prevDay": {"c": 100.0},
            "lastQuote": {"p": 102.99, "P": 103.01},
        }
    )

    assert result["snapshot_score"] == 2
    assert result["snapshot"]["gap_pct"] == 3.0
    assert result["risk_flags"] == []


def test_combine_intelligence_catalogs_evidence_and_context_without_scoring():
    result = combine_intelligence(
        news=[{"title": "ACME launches new AI product", "published_utc": "2026-06-29T12:00:00Z"}],
        snapshot={"day": {"c": 90, "v": 100_000}, "prevDay": {"c": 100}},
        details={"name": "ACME", "market_cap": 500_000_000, "type": "CS", "active": True},
    )

    assert result["intel_score"] == 0
    assert result["news_score"] == 0
    assert result["snapshot_score"] == 0
    assert result["details_score"] == 0
    assert result["catalog_only"] is True
    assert result["catalysts"]
    assert "thin_volume" in result["risk_flags"]
    assert "small_cap" in result["risk_flags"]


@pytest.mark.asyncio
async def test_enrich_recommendations_adds_catalog_without_provider_key():
    class DummyClient:
        async def get(self, *args, **kwargs):  # pragma: no cover - should not be called without key
            raise AssertionError("should not fetch without api key")

    recs = [{"ticker": "AAPL", "score": 7, "screens": ["double_bottom"]}]
    enriched = await enrich_recommendations(DummyClient(), recs, api_key=None)

    assert enriched[0]["ta_score"] == 7
    assert enriched[0]["intel_score"] == 0
    assert enriched[0]["final_score"] == 7
    assert enriched[0]["news_policy"] == "catalog_only_not_scored"
    assert "market_intel" in enriched[0]


@pytest.mark.asyncio
async def test_enrich_recommendations_preserves_ta_order_even_with_strong_news():
    class FakeResponse:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    class FakeClient:
        async def get(self, path, params=None):
            ticker = params.get("ticker") if params else None
            if path == "/v2/reference/news" and ticker == "LOWTA":
                return FakeResponse(
                    {
                        "results": [
                            {
                                "title": "LOWTA raises guidance after earnings beat",
                                "published_utc": "2026-06-29T12:00:00Z",
                                "publisher": {"name": "Newswire"},
                            }
                        ]
                    }
                )
            if path.startswith("/v3/reference/tickers/"):
                return FakeResponse({"results": {"name": ticker, "market_cap": 100_000_000_000, "type": "CS", "active": True}})
            if path.startswith("/v2/snapshot/"):
                return FakeResponse({"ticker": {"day": {"c": 100, "v": 10_000_000}, "prevDay": {"c": 99}}})
            return FakeResponse({"results": []})

    recs = [
        {"ticker": "HIGHTA", "score": 10, "screens": ["double_bottom"]},
        {"ticker": "LOWTA", "score": 3, "screens": ["volume_support"]},
    ]
    enriched = await enrich_recommendations(FakeClient(), recs, api_key="test-key")

    assert [r["ticker"] for r in enriched] == ["HIGHTA", "LOWTA"]
    assert [r["final_score"] for r in enriched] == [10, 3]
    assert enriched[1]["market_intel"]["catalysts"][0]["type"] == "earnings_beat"
    assert enriched[1]["market_intel"]["catalysts"][0]["catalog_only"] is True
