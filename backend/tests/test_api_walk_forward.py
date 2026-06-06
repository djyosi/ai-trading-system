from fastapi.testclient import TestClient

from app.main import app


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


def test_walk_forward_api_rejects_too_few_candles_for_lookback():
    client = TestClient(app)

    response = client.post(
        "/api/backtests/walk-forward",
        json={"ticker": "PAX", "candles": [_candle(1, 10.0, 9.6, 9.9)], "lookback_bars": 3, "horizon_bars": 1},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Not enough candles for requested lookback"
