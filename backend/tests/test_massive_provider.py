from datetime import datetime, timezone

import httpx
import pytest

from app.core.config import Settings
from app.providers.massive import MassiveProvider, ProviderConfigurationError


@pytest.mark.asyncio
async def test_massive_provider_requires_api_key():
    provider = MassiveProvider(Settings(massive_api_key=None))

    with pytest.raises(ProviderConfigurationError, match="MASSIVE_API_KEY"):
        await provider.get_snapshot("AAPL")


@pytest.mark.asyncio
async def test_get_daily_candles_normalizes_aggregate_response():
    async def handler(request):
        assert request.url.params["apiKey"] == "test-key"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "t": 1717200000000,
                        "o": 100.0,
                        "h": 110.0,
                        "l": 95.0,
                        "c": 108.0,
                        "v": 1234567,
                        "vw": 103.5,
                        "n": 321,
                    }
                ]
            },
        )

    provider = MassiveProvider(
        Settings(massive_api_key="test-key"),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.massive.com"),
    )

    candles = await provider.get_daily_candles(
        "AAPL",
        datetime(2024, 6, 1, tzinfo=timezone.utc),
        datetime(2024, 6, 2, tzinfo=timezone.utc),
    )

    assert candles == [
        {
            "ticker": "AAPL",
            "provider": "massive",
            "timeframe": "1d",
            "timestamp_ms": 1717200000000,
            "open": 100.0,
            "high": 110.0,
            "low": 95.0,
            "close": 108.0,
            "volume": 1234567,
            "vwap": 103.5,
            "transactions": 321,
            "raw": {
                "t": 1717200000000,
                "o": 100.0,
                "h": 110.0,
                "l": 95.0,
                "c": 108.0,
                "v": 1234567,
                "vw": 103.5,
                "n": 321,
            },
        }
    ]

    await provider.aclose()


@pytest.mark.asyncio
async def test_get_snapshot_returns_normalized_snapshot():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "ticker": {
                    "ticker": "MSFT",
                    "day": {"c": 450.25, "v": 987654},
                    "prevDay": {"c": 440.00},
                    "lastQuote": {"P": 450.30, "p": 450.20},
                }
            },
        )

    provider = MassiveProvider(
        Settings(massive_api_key="test-key"),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.massive.com"),
    )

    snapshot = await provider.get_snapshot("MSFT")

    assert snapshot["ticker"] == "MSFT"
    assert snapshot["price"] == 450.25
    assert snapshot["volume"] == 987654
    assert snapshot["previous_close"] == 440.00
    assert snapshot["bid"] == 450.20
    assert snapshot["ask"] == 450.30
    assert snapshot["provider"] == "massive"
    await provider.aclose()


def test_massive_news_catalyst_type_inference_covers_common_research_catalysts():
    provider = MassiveProvider(Settings(massive_api_key="test-key"))

    cases = [
        ("Apple unveils new AI product line", None, "product_launch"),
        ("Amazon to acquire robotics startup", None, "m_and_a"),
        ("Tesla misses earnings estimates", "Quarterly profit missed expectations", "earnings_miss"),
        ("Justice Department opens investigation into Alphabet", None, "investigation"),
        ("Pfizer wins FDA clearance for new treatment", None, "fda_approval"),
        ("Exxon forms strategic partnership with lithium startup", None, "partnership"),
        ("Apple announces $110 billion share buyback program", None, "buyback"),
        ("Microsoft raises dividend by 10%", None, "dividend"),
        ("Moderna begins phase 3 clinical trial for RSV vaccine", None, "fda_clinical"),
        ("Goldman Sachs initiates coverage of Rivian with buy rating", None, "analyst_initiation"),
        ("Moody's upgrades Apple credit rating to AAA", None, "credit_rating"),
        ("Company announces special dividend of $2 per share", None, "dividend"),
    ]

    for headline, description, expected in cases:
        assert provider._infer_news_catalyst_type(headline, description) == expected


@pytest.mark.asyncio
async def test_get_news_normalizes_massive_news_response_as_catalysts():
    async def handler(request):
        assert request.url.path == "/v2/reference/news"
        assert request.url.params["ticker"] == "NVDA"
        assert request.url.params["apiKey"] == "test-key"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "news-1",
                        "title": "NVDA raises guidance after earnings beat",
                        "description": "Revenue guidance was raised.",
                        "published_utc": "2025-01-03T14:30:00Z",
                        "article_url": "https://example.com/nvda",
                        "publisher": {"name": "Example News"},
                        "tickers": ["NVDA"],
                    }
                ]
            },
        )

    provider = MassiveProvider(
        Settings(massive_api_key="test-key"),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.massive.com"),
    )

    news = await provider.get_news("NVDA", "2025-01-01", "2025-01-05")

    assert news == [
        {
            "provider": "massive",
            "ticker": "NVDA",
            "external_id": "news-1",
            "headline": "NVDA raises guidance after earnings beat",
            "summary": "Revenue guidance was raised.",
            "published_utc": "2025-01-03T14:30:00Z",
            "timestamp_ms": 1735914600000,
            "source": "Example News",
            "url": "https://example.com/nvda",
            "catalyst_type": "earnings_beat",
            "raw": {
                "id": "news-1",
                "title": "NVDA raises guidance after earnings beat",
                "description": "Revenue guidance was raised.",
                "published_utc": "2025-01-03T14:30:00Z",
                "article_url": "https://example.com/nvda",
                "publisher": {"name": "Example News"},
                "tickers": ["NVDA"],
            },
        }
    ]

    await provider.aclose()
