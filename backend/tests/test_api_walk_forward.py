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


def test_batch_backtest_api_can_use_liquid_research_universe_preset():
    class FakeProvider:
        def __init__(self):
            self.calls = []

        async def get_daily_candles(self, ticker, start, end):
            self.calls.append(ticker)
            return [_candle(i, 100 + i, 99 + i, 99.5 + i) for i in range(1, 7)]

    provider = FakeProvider()
    app.dependency_overrides[get_backtest_market_data_provider] = lambda: provider
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={
            "universe_preset": "liquid_research_25",
            "start": "2025-01-01",
            "end": "2025-02-01",
            "lookback_bars": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe_preset"] == "liquid_research_25"
    assert payload["tickers_total"] == 25
    assert provider.calls[:5] == ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]
    assert provider.calls[-1] == "XOM"
    app.dependency_overrides.clear()


def test_batch_backtest_api_can_use_broad_liquid_research_universe_preset():
    class FakeProvider:
        def __init__(self):
            self.calls = []

        async def get_daily_candles(self, ticker, start, end):
            self.calls.append(ticker)
            return [_candle(i, 100 + i, 99 + i, 99.5 + i) for i in range(1, 7)]

    provider = FakeProvider()
    app.dependency_overrides[get_backtest_market_data_provider] = lambda: provider
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={
            "universe_preset": "liquid_research_100",
            "start": "2025-01-01",
            "end": "2025-02-01",
            "lookback_bars": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe_preset"] == "liquid_research_100"
    assert payload["tickers_total"] == 100
    assert provider.calls[:5] == ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]
    assert provider.calls[49] == "DIA"
    assert provider.calls[-1] == "ABNB"
    assert len(set(provider.calls)) == 100
    app.dependency_overrides.clear()


def test_batch_backtest_api_can_use_sector_universe_preset():
    class FakeProvider:
        def __init__(self):
            self.calls = []

        async def get_daily_candles(self, ticker, start, end):
            self.calls.append(ticker)
            return [_candle(i, 100 + i, 99 + i, 99.5 + i) for i in range(1, 7)]

    provider = FakeProvider()
    app.dependency_overrides[get_backtest_market_data_provider] = lambda: provider
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={
            "universe_preset": "sector_semiconductors",
            "start": "2025-01-01",
            "end": "2025-02-01",
            "lookback_bars": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe_preset"] == "sector_semiconductors"
    assert payload["tickers_total"] == 12
    assert provider.calls[:5] == ["NVDA", "AMD", "AVGO", "SMCI", "MU"]
    assert provider.calls[-1] == "ASML"
    assert len(set(provider.calls)) == 12
    app.dependency_overrides.clear()


def test_batch_backtest_api_rejects_unknown_universe_preset():
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={"universe_preset": "not_real", "start": "2025-01-01", "end": "2025-02-01"},
    )

    assert response.status_code == 400
    assert "Unknown universe preset 'not_real'" in response.json()["detail"]


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


def test_batch_backtest_api_can_include_paper_validation_summary():
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
            "lookback_bars": 3,
            "horizon_bars": 1,
            "market_context": {"risk_context": "supportive", "spy_trend": "up", "qqq_trend": "up"},
            "catalysts_by_ticker": {
                "AAPL": [{"catalyst_type": "analyst_upgrade", "timestamp_ms": 4 * 86_400_000}]
            },
            "include_paper_validation": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["paper_validation"]["mode"] == "paper_simulation"
    assert payload["paper_validation"]["orders_enabled"] is False
    assert payload["paper_validation"]["summary"]["recommendations_total"] == 2
    assert "evidence_backed" in payload["paper_validation"]["by_evidence_bucket"]
    assert (
        payload["paper_validation"]["by_market_context_segment"]
        ["catalyst_momentum_gap_and_go|analyst_upgrade|supportive"]["recommendations_total"]
        >= 1
    )
    app.dependency_overrides.clear()


def test_batch_backtest_api_can_fetch_provider_market_context():
    class FakeProvider:
        def __init__(self):
            self.calls = []

        async def get_daily_candles(self, ticker, start, end):
            self.calls.append({"ticker": ticker, "start": start, "end": end})
            if ticker == "SPY":
                return [_candle(i, 100 + i, 99 + i, 100 + i) for i in range(1, 8)]
            if ticker == "QQQ":
                return [_candle(i, 200 + i * 2, 199 + i * 2, 200 + i * 2) for i in range(1, 8)]
            if ticker == "IWM":
                return [_candle(i, 190, 189, 190) for i in range(1, 8)]
            return [_candle(i, 10 + i, 9 + i, 9.5 + i) for i in range(1, 8)]

    provider = FakeProvider()
    app.dependency_overrides[get_backtest_market_data_provider] = lambda: provider
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={
            "tickers": ["AAPL"],
            "start": "2025-01-01",
            "end": "2025-02-01",
            "lookback_bars": 3,
            "horizon_bars": 1,
            "include_market_context": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["market_context"] == {
        "spy_trend": "up",
        "qqq_trend": "up",
        "iwm_trend": "neutral",
        "risk_context": "supportive",
    }
    assert payload["market_context_source"] == "provider_etfs"
    first = payload["results"]["AAPL"]["items"][0]
    later = payload["results"]["AAPL"]["items"][1]
    assert first["recommendation"]["inputs"]["market_context"]["risk_context"] == "mixed"
    assert later["recommendation"]["inputs"]["market_context"]["risk_context"] == "supportive"
    assert provider.calls[:3] == [
        {"ticker": "SPY", "start": "2025-01-01", "end": "2025-02-01"},
        {"ticker": "QQQ", "start": "2025-01-01", "end": "2025-02-01"},
        {"ticker": "IWM", "start": "2025-01-01", "end": "2025-02-01"},
    ]
    app.dependency_overrides.clear()


def test_batch_backtest_api_builds_timestamp_market_context_from_provider_etfs():
    class FakeProvider:
        async def get_daily_candles(self, ticker, start, end):
            if ticker in {"SPY", "QQQ"}:
                closes = [100, 101, 102, 103, 104, 90, 89, 88]
                return [_candle(i, close + 0.2, close + 0.5, close) for i, close in enumerate(closes, start=1)]
            if ticker == "IWM":
                return [_candle(i, 190, 189, 190) for i in range(1, 9)]
            return [_candle(i, 210 + i, 209 + i, 210 + i) for i in range(1, 9)]

    app.dependency_overrides[get_backtest_market_data_provider] = lambda: FakeProvider()
    client = TestClient(app)

    response = client.post(
        "/api/backtests/batch",
        json={
            "tickers": ["AAPL"],
            "start": "2025-01-01",
            "end": "2025-02-01",
            "lookback_bars": 3,
            "horizon_bars": 1,
            "include_market_context": True,
            "actionable_score_threshold": 20,
        },
    )

    assert response.status_code == 200
    items = response.json()["results"]["AAPL"]["items"]
    assert items[1]["recommendation"]["inputs"]["market_context"]["risk_context"] == "supportive"
    assert items[2]["recommendation"]["inputs"]["market_context"]["risk_context"] == "risk_off"
    assert items[2]["recommendation"]["status"] == "caution"
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


def test_walk_forward_api_threshold_sweep_defaults_include_research_thresholds():
    client = TestClient(app)
    candles = [
        _candle(1, 209.0, 208.0, 210.0, volume=5_000_000),
        _candle(2, 210.0, 209.0, 211.0, volume=5_000_000),
        _candle(3, 211.0, 210.0, 212.0, volume=5_000_000),
        _candle(4, 212.5, 211.5, 213.0, volume=5_000_000),
        _candle(5, 216.5, 212.0, 216.0, volume=5_000_000),
    ]

    response = client.post(
        "/api/backtests/walk-forward",
        json={
            "ticker": "AAPL",
            "candles": candles,
            "market_context": {"risk_context": "supportive"},
            "lookback_bars": 3,
            "horizon_bars": 1,
            "actionable_score_threshold": 30,
            "include_threshold_sweep": True,
        },
    )

    assert response.status_code == 200
    assert [row["threshold"] for row in response.json()["threshold_sweep"]["thresholds"]][:2] == [30, 40]


def test_walk_forward_api_applies_actionable_score_threshold():
    client = TestClient(app)
    candles = [
        {"timestamp_ms": i * 86_400_000, "open": 210 + i, "high": 210.5 + i, "low": 209.5 + i, "close": 210 + i, "volume": 5_000_000}
        for i in range(1, 6)
    ]

    response = client.post(
        "/api/backtests/walk-forward",
        json={
            "ticker": "AAPL",
            "candles": candles,
            "market_context": {"risk_context": "mixed"},
            "lookback_bars": 3,
            "horizon_bars": 1,
            "actionable_score_threshold": 20,
        },
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["recommendation"]["status"] == "active_watch"


def test_batch_backtest_api_applies_actionable_score_threshold():
    class FakeProvider:
        async def get_daily_candles(self, ticker, start, end):
            return [
                {"timestamp_ms": i * 86_400_000, "open": 210 + i, "high": 210.5 + i, "low": 209.5 + i, "close": 210 + i, "volume": 5_000_000}
                for i in range(1, 6)
            ]

    app.dependency_overrides[get_backtest_market_data_provider] = lambda: FakeProvider()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/backtests/batch",
            json={
                "tickers": ["AAPL"],
                "data_source": "provider",
                "start": "2026-01-01",
                "end": "2026-01-31",
                "lookback_bars": 3,
                "horizon_bars": 1,
                "actionable_score_threshold": 20,
            },
        )
    finally:
        app.dependency_overrides.pop(get_backtest_market_data_provider, None)

    assert response.status_code == 200
    assert response.json()["results"]["AAPL"]["items"][0]["recommendation"]["status"] == "active_watch"


def test_walk_forward_api_rejects_too_few_candles_for_lookback():
    client = TestClient(app)

    response = client.post(
        "/api/backtests/walk-forward",
        json={"ticker": "PAX", "candles": [_candle(1, 10.0, 9.6, 9.9)], "lookback_bars": 3, "horizon_bars": 1},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Not enough candles for requested lookback"
