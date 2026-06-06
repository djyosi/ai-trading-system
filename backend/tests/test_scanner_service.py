import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.repositories.recommendations import RecommendationRepository
from app.scanner.service import ScannerService


class FakeMarketDataProvider:
    async def get_snapshot(self, ticker):
        snapshots = {
            "PAX": {
                "ticker": "PAX",
                "price": 11.55,
                "previous_close": 10.74,
                "volume": 3_200_000,
                "bid": 11.54,
                "ask": 11.56,
            },
            "THIN": {
                "ticker": "THIN",
                "price": 3.20,
                "previous_close": 3.10,
                "volume": 20_000,
                "bid": 3.00,
                "ask": 3.30,
            },
        }
        return snapshots[ticker]

    async def get_daily_candles(self, ticker, start, end):
        if ticker == "THIN":
            return [
                {"high": 3.3, "low": 3.0, "close": 3.1, "volume": 20_000},
                {"high": 3.4, "low": 3.1, "close": 3.2, "volume": 18_000},
                {"high": 3.3, "low": 3.0, "close": 3.2, "volume": 19_000},
            ]
        return [
            {"high": 10.3, "low": 9.8, "close": 10.0, "volume": 900_000},
            {"high": 10.8, "low": 10.1, "close": 10.6, "volume": 1_000_000},
            {"high": 11.0, "low": 10.5, "close": 10.74, "volume": 1_000_000},
        ]

    async def get_intraday_candles(self, ticker, start, end, timeframe="1m"):
        if ticker == "THIN":
            return [
                {"high": 3.2, "low": 3.1, "close": 3.15, "volume": 2_000},
                {"high": 3.25, "low": 3.1, "close": 3.2, "volume": 2_100},
            ]
        return [
            {"high": 11.45, "low": 11.10, "close": 11.30, "volume": 120_000},
            {"high": 11.70, "low": 11.25, "close": 11.55, "volume": 180_000},
            {"high": 11.85, "low": 11.40, "close": 11.60, "volume": 210_000},
        ]


class FakeCatalystProvider:
    async def get_catalysts(self, ticker):
        if ticker == "THIN":
            return [{"ticker": ticker, "catalyst_type": "unknown", "event_age_minutes": 120}]
        return [
            {
                "ticker": ticker,
                "catalyst_type": "insider_director_purchase",
                "event_age_minutes": 20,
                "summary": "Director open-market purchase.",
            }
        ]


class FakeMarketContextProvider:
    async def get_market_context(self):
        return {
            "spy_trend": "up",
            "qqq_trend": "up",
            "iwm_trend": "neutral",
            "risk_context": "supportive",
        }


def _repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return RecommendationRepository(sessionmaker(bind=engine)())


@pytest.mark.asyncio
async def test_scanner_builds_and_persists_active_watch_recommendation():
    repo = _repo()
    scanner = ScannerService(
        market_data_provider=FakeMarketDataProvider(),
        catalyst_provider=FakeCatalystProvider(),
        market_context_provider=FakeMarketContextProvider(),
        recommendation_repository=repo,
    )

    results = await scanner.scan(["PAX"])

    assert len(results) == 1
    recommendation = results[0]
    assert recommendation["ticker"] == "PAX"
    assert recommendation["status"] == "active_watch"
    assert recommendation["inputs"]["features"]["gap_percent"] == 7.54
    assert recommendation["inputs"]["features"]["relative_volume"] == 3.31
    persisted = repo.list_recommendations()
    assert len(persisted) == 1
    assert persisted[0].ticker == "PAX"
    assert persisted[0].input_snapshot["features"]["gap_percent"] == 7.54


@pytest.mark.asyncio
async def test_scanner_persists_no_trade_rejection_for_learning():
    repo = _repo()
    scanner = ScannerService(
        market_data_provider=FakeMarketDataProvider(),
        catalyst_provider=FakeCatalystProvider(),
        market_context_provider=FakeMarketContextProvider(),
        recommendation_repository=repo,
    )

    results = await scanner.scan(["THIN"])

    assert results[0]["status"] == "no_trade"
    assert "price_below_min" in results[0]["reject_reasons"]
    assert "liquidity_score_below_min" in results[0]["reject_reasons"]
    assert repo.list_recommendations()[0].status == "no_trade"


@pytest.mark.asyncio
async def test_scanner_continues_when_one_symbol_provider_fails():
    class FailingForThinMarketData(FakeMarketDataProvider):
        async def get_snapshot(self, ticker):
            if ticker == "THIN":
                raise RuntimeError("provider unavailable")
            return await super().get_snapshot(ticker)

    repo = _repo()
    scanner = ScannerService(
        market_data_provider=FailingForThinMarketData(),
        catalyst_provider=FakeCatalystProvider(),
        market_context_provider=FakeMarketContextProvider(),
        recommendation_repository=repo,
    )

    results = await scanner.scan(["THIN", "PAX"])

    assert len(results) == 2
    assert results[0] == {
        "ticker": "THIN",
        "status": "error",
        "error": "provider unavailable",
    }
    assert results[1]["ticker"] == "PAX"
    assert results[1]["status"] == "active_watch"
    assert len(repo.list_recommendations()) == 1
