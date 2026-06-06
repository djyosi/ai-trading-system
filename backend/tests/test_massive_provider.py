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
