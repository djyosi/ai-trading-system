from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.backtests import get_backtest_market_data_provider
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.repositories.recommendations import RecommendationRepository


def _candle(index, high, low, close, volume=1_000_000):
    return {
        "timestamp_ms": index * 86_400_000,
        "open": close - 0.2,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "vwap": round((high + low + close) / 3, 2),
    }


class FakeHistoricalProvider:
    def __init__(self):
        self.calls = []

    async def get_daily_candles(self, ticker, start, end):
        self.calls.append({"ticker": ticker, "start": start, "end": end})
        return [
            _candle(1, 10.0, 9.6, 9.9),
            _candle(2, 10.2, 9.7, 10.0),
            _candle(3, 10.4, 9.8, 10.1),
            _candle(4, 11.8, 10.7, 11.5, volume=3_200_000),
            _candle(5, 12.8, 11.4, 12.4, volume=2_400_000),
        ]


def test_walk_forward_api_runs_replay_from_request_payload():
    client = TestClient(app)
    candles = [
        _candle(1, 10.0, 9.6, 9.9),
        _candle(2, 10.2, 9.7, 10.0),
        _candle(3, 10.4, 9.8, 10.1),
        _candle(4, 11.8, 10.7, 11.5, volume=3_200_000),
        _candle(5, 12.8, 11.4, 12.4, volume=2_400_000),
    ]

    response = client.post(
        "/api/backtests/walk-forward",
        json={
            "ticker": "PAX",
            "candles": candles,
            "catalysts": [
                {
                    "type": "earnings_beat",
                    "summary": "Earnings beat and raised guidance",
                    "timestamp_ms": candles[3]["timestamp_ms"],
                }
            ],
            "market_context": {"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
            "lookback_bars": 3,
            "horizon_bars": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "PAX"
    assert payload["evaluated_bars"] == 2
    assert payload["summary"]["closed_total"] >= 1
    assert payload["items"][0]["recommendation"]["inputs"]["walk_forward"]["visible_candle_count"] == 4


def test_walk_forward_api_fetches_daily_candles_from_market_data_provider_when_requested():
    provider = FakeHistoricalProvider()
    app.dependency_overrides[get_backtest_market_data_provider] = lambda: provider
    client = TestClient(app)

    try:
        response = client.post(
            "/api/backtests/walk-forward",
            json={
                "ticker": "AAPL",
                "source": "massive",
                "start": "2025-01-01",
                "end": "2025-01-10",
                "lookback_bars": 3,
                "horizon_bars": 1,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert provider.calls == [{"ticker": "AAPL", "start": "2025-01-01", "end": "2025-01-10"}]
    assert payload["ticker"] == "AAPL"
    assert payload["data_source"] == "massive"
    assert payload["source_candle_count"] == 5
    assert payload["evaluated_bars"] == 2


def test_walk_forward_api_requires_start_and_end_for_provider_backtests():
    client = TestClient(app)

    response = client.post(
        "/api/backtests/walk-forward",
        json={"ticker": "AAPL", "source": "massive", "lookback_bars": 3, "horizon_bars": 1},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "start and end are required when source is massive"


def test_walk_forward_api_includes_threshold_sweep_when_requested():
    client = TestClient(app)
    candles = [
        _candle(1, 10.0, 9.6, 9.9),
        _candle(2, 10.2, 9.7, 10.0),
        _candle(3, 10.4, 9.8, 10.1),
        _candle(4, 11.8, 10.7, 11.5, volume=3_200_000),
        _candle(5, 12.8, 11.4, 12.4, volume=2_400_000),
    ]

    response = client.post(
        "/api/backtests/walk-forward",
        json={
            "ticker": "PAX",
            "candles": candles,
            "catalysts": [{"type": "earnings_beat", "timestamp_ms": candles[3]["timestamp_ms"]}],
            "market_context": {"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
            "lookback_bars": 3,
            "horizon_bars": 1,
            "thresholds": [60, 80],
            "include_threshold_sweep": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["threshold_sweep"]["thresholds"][0]["threshold"] == 60
    assert payload["threshold_tuning_by_segment"]


def _client_with_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def test_walk_forward_api_can_persist_replay_recommendations_and_outcomes():
    client, SessionLocal = _client_with_db()
    candles = [
        _candle(1, 10.0, 9.6, 9.9),
        _candle(2, 10.2, 9.7, 10.0),
        _candle(3, 10.4, 9.8, 10.1),
        _candle(4, 11.8, 10.7, 11.5, volume=3_200_000),
        _candle(5, 12.8, 11.4, 12.4, volume=2_400_000),
    ]

    response = client.post(
        "/api/backtests/walk-forward",
        json={
            "ticker": "PAX",
            "candles": candles,
            "catalysts": [{"type": "earnings_beat", "timestamp_ms": candles[3]["timestamp_ms"]}],
            "market_context": {"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
            "lookback_bars": 3,
            "horizon_bars": 1,
            "persist_recommendations": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["persisted_recommendations"] == 2
    db = SessionLocal()
    try:
        records = RecommendationRepository(db).list_recommendations()
        assert len(records) == 2
        assert records[0].outcome is not None
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_batch_backtest_api_runs_multiple_tickers_with_provider_dependency():
    class FakeProvider:
        async def get_daily_candles(self, ticker, start, end):
            return [_candle(i, 10 + i, 9 + i, 9.5 + i) for i in range(1, 7)]

    app.dependency_overrides[get_backtest_market_data_provider] = lambda: FakeProvider()
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={"tickers": ["AAPL", "MSFT"], "start": "2025-01-01", "end": "2025-02-01", "lookback_bars": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tickers_completed"] == 2
    assert payload["evaluated_bars_total"] == 6
    app.dependency_overrides.clear()


def test_batch_backtest_api_can_return_aggregate_threshold_tuning():
    class FakeProvider:
        async def get_daily_candles(self, ticker, start, end):
            return [_candle(i, 10 + i, 9 + i, 9.5 + i) for i in range(1, 8)]

    app.dependency_overrides[get_backtest_market_data_provider] = lambda: FakeProvider()
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={
            "tickers": ["AAPL", "MSFT"],
            "start": "2025-01-01",
            "end": "2025-02-01",
            "lookback_bars": 3,
            "horizon_bars": 1,
            "include_threshold_sweep": True,
            "thresholds": [60, 80],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["aggregate_threshold_sweep"]["thresholds"][0]["threshold"] == 60
    assert "best_threshold" in payload["aggregate_threshold_sweep"]
    app.dependency_overrides.clear()


def test_batch_backtest_api_can_return_research_report():
    class FakeProvider:
        async def get_daily_candles(self, ticker, start, end):
            return [_candle(i, 10 + i, 9 + i, 9.5 + i) for i in range(1, 8)]

    app.dependency_overrides[get_backtest_market_data_provider] = lambda: FakeProvider()
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={
            "tickers": ["AAPL", "MSFT"],
            "start": "2025-01-01",
            "end": "2025-02-01",
            "lookback_bars": 3,
            "horizon_bars": 1,
            "include_threshold_sweep": True,
            "include_research_report": True,
            "thresholds": [60, 80],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["research_report"]["coverage"]["tickers_completed"] == 2
    assert payload["research_report"]["status"] in {"research_ready", "needs_more_data"}
    assert "warnings" in payload["research_report"]
    app.dependency_overrides.clear()


def test_batch_backtest_api_can_fetch_provider_news_catalysts_per_ticker():
    class FakeProvider:
        def __init__(self):
            self.news_calls = []

        async def get_daily_candles(self, ticker, start, end):
            return [_candle(i, 10 + i, 9 + i, 9.5 + i) for i in range(1, 8)]

        async def get_news(self, ticker, start, end):
            self.news_calls.append({"ticker": ticker, "start": start, "end": end})
            return [{"type": "earnings_beat", "timestamp_ms": 3 * 86_400_000, "headline": f"{ticker} beats"}]

    provider = FakeProvider()
    app.dependency_overrides[get_backtest_market_data_provider] = lambda: provider
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={
            "tickers": ["AAPL", "MSFT"],
            "start": "2025-01-01",
            "end": "2025-02-01",
            "lookback_bars": 3,
            "horizon_bars": 1,
            "include_news_catalysts": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert provider.news_calls == [
        {"ticker": "AAPL", "start": "2025-01-01", "end": "2025-02-01"},
        {"ticker": "MSFT", "start": "2025-01-01", "end": "2025-02-01"},
    ]
    assert payload["news_catalysts_fetched"] == 2
    assert payload["results"]["AAPL"]["items"][0]["recommendation"]["inputs"]["catalyst"]["catalyst_type"] == "earnings_beat"
    app.dependency_overrides.clear()


def test_walk_forward_api_applies_catalyst_freshness_window():
    client = TestClient(app)
    candles = [
        _candle(1, 10.0, 9.6, 9.9),
        _candle(2, 10.2, 9.7, 10.0),
        _candle(3, 10.4, 9.8, 10.1),
        _candle(4, 11.8, 10.7, 11.5, volume=3_200_000),
        _candle(5, 12.8, 11.4, 12.4, volume=2_400_000),
    ]

    response = client.post(
        "/api/backtests/walk-forward",
        json={
            "ticker": "AAPL",
            "candles": candles,
            "catalysts": [{"type": "earnings_beat", "timestamp_ms": candles[0]["timestamp_ms"]}],
            "market_context": {"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
            "lookback_bars": 3,
            "horizon_bars": 1,
            "catalyst_max_age_minutes": 60,
        },
    )

    assert response.status_code == 200
    first = response.json()["items"][0]
    assert first["recommendation"]["inputs"]["catalyst"]["catalyst_type"] == "unknown"


def test_batch_backtest_api_applies_catalyst_freshness_window():
    class FakeProvider:
        async def get_daily_candles(self, ticker, start, end):
            return [
                _candle(1, 10.0, 9.6, 9.9),
                _candle(2, 10.2, 9.7, 10.0),
                _candle(3, 10.4, 9.8, 10.1),
                _candle(4, 11.8, 10.7, 11.5, volume=3_200_000),
                _candle(5, 12.8, 11.4, 12.4, volume=2_400_000),
            ]

    app.dependency_overrides[get_backtest_market_data_provider] = lambda: FakeProvider()
    client = TestClient(app)
    response = client.post(
        "/api/backtests/batch",
        json={
            "tickers": ["AAPL"],
            "start": "2025-01-01",
            "end": "2025-02-01",
            "catalysts_by_ticker": {"AAPL": [{"type": "earnings_beat", "timestamp_ms": 86_400_000}]},
            "lookback_bars": 3,
            "horizon_bars": 1,
            "catalyst_max_age_minutes": 60,
        },
    )

    assert response.status_code == 200
    first = response.json()["results"]["AAPL"]["items"][0]
    assert first["recommendation"]["inputs"]["catalyst"]["catalyst_type"] == "unknown"
    app.dependency_overrides.clear()


def test_walk_forward_api_rejects_too_few_candles_for_lookback():
    client = TestClient(app)

    response = client.post(
        "/api/backtests/walk-forward",
        json={"ticker": "PAX", "candles": [_candle(1, 10.0, 9.6, 9.9)], "lookback_bars": 3, "horizon_bars": 1},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Not enough candles for requested lookback"
