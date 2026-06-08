from fastapi.testclient import TestClient

from app.main import app


def _recommendation(evidence=True):
    recommendation = {
        "ticker": "AAPL",
        "direction": "long",
        "status": "active_watch",
        "entry_zone": [10.0, 10.2],
        "stop_loss": 9.5,
        "targets": [11.0],
        "strategy": "vwap_hold_reclaim",
        "strategy_segment": "vwap_hold_reclaim|contract_win",
        "research_tags": ["segment_edge_candidate"],
        "research_evidence": None,
    }
    if evidence:
        recommendation["research_tags"].append("market_context_edge_candidate")
        recommendation["research_evidence"] = {
            "market_context_segment": "vwap_hold_reclaim|contract_win|supportive",
            "recommended_threshold": 60,
            "trade_count": 74,
            "win_rate": 0.45,
            "expectancy_r": 0.11,
        }
    return recommendation


def _candle(index, high, low, close):
    return {"timestamp_ms": index, "high": high, "low": low, "close": close}


def test_paper_validation_api_summarizes_payload_recommendations_without_enabling_orders():
    client = TestClient(app)

    response = client.post(
        "/api/paper-trading/validate",
        json={
            "account_equity": 100000,
            "risk_fraction": 0.01,
            "items": [
                {
                    "recommendation": _recommendation(evidence=True),
                    "candles": [_candle(1, 10.1, 9.9, 10.05), _candle(2, 11.2, 10.2, 11.0)],
                },
                {
                    "recommendation": _recommendation(evidence=False),
                    "candles": [_candle(1, 10.1, 9.9, 10.05), _candle(2, 10.2, 9.4, 9.5)],
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "paper_simulation"
    assert payload["orders_enabled"] is False
    assert payload["data_source"] == "request_payload"
    assert payload["summary"]["expectancy_r"] == 0.25
    assert payload["by_evidence_bucket"]["evidence_backed"]["expectancy_r"] == 1.5
    assert payload["by_evidence_bucket"]["baseline"]["expectancy_r"] == -1.0
    assert payload["by_market_context_segment"]["vwap_hold_reclaim|contract_win|supportive"]["closed_total"] == 1
