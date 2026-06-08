from app.paper_trading.validation import validate_paper_recommendations


def _recommendation(ticker="AAPL", evidence=True):
    recommendation = {
        "ticker": ticker,
        "direction": "long",
        "status": "active_watch",
        "entry_zone": [10.0, 10.2],
        "stop_loss": 9.5,
        "targets": [11.0, 12.0],
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


def test_paper_validation_summarizes_evidence_backed_recommendations_vs_baseline():
    result = validate_paper_recommendations(
        [
            {
                "recommendation": _recommendation("EVIDENCE_WIN", evidence=True),
                "candles": [_candle(1, 10.1, 9.9, 10.05), _candle(2, 11.2, 10.2, 11.0)],
            },
            {
                "recommendation": _recommendation("BASELINE_LOSS", evidence=False),
                "candles": [_candle(1, 10.1, 9.9, 10.05), _candle(2, 10.2, 9.4, 9.5)],
            },
        ],
        account_equity=100_000,
        risk_fraction=0.01,
    )

    assert result["summary"] == {
        "recommendations_total": 2,
        "closed_total": 2,
        "skipped_total": 0,
        "not_triggered_total": 0,
        "wins": 1,
        "losses": 1,
        "win_rate": 0.5,
        "average_realized_r": 0.25,
        "expectancy_r": 0.25,
    }
    assert result["by_evidence_bucket"] == {
        "baseline": {
            "recommendations_total": 1,
            "closed_total": 1,
            "skipped_total": 0,
            "not_triggered_total": 0,
            "wins": 0,
            "losses": 1,
            "win_rate": 0.0,
            "average_realized_r": -1.0,
            "expectancy_r": -1.0,
        },
        "evidence_backed": {
            "recommendations_total": 1,
            "closed_total": 1,
            "skipped_total": 0,
            "not_triggered_total": 0,
            "wins": 1,
            "losses": 0,
            "win_rate": 1.0,
            "average_realized_r": 1.5,
            "expectancy_r": 1.5,
        },
    }
    assert result["items"][0]["paper_result"]["realized_r"] == 1.5
    assert result["items"][1]["paper_result"]["realized_r"] == -1.0


def test_paper_validation_groups_evidence_backed_results_by_market_context_segment():
    result = validate_paper_recommendations(
        [
            {
                "recommendation": _recommendation("EVIDENCE_WIN", evidence=True),
                "candles": [_candle(1, 10.1, 9.9, 10.05), _candle(2, 11.2, 10.2, 11.0)],
            },
            {
                "recommendation": _recommendation("NO_TRIGGER", evidence=True),
                "candles": [_candle(1, 9.8, 9.2, 9.4)],
            },
        ]
    )

    assert result["by_market_context_segment"] == {
        "vwap_hold_reclaim|contract_win|supportive": {
            "recommendations_total": 2,
            "closed_total": 1,
            "skipped_total": 0,
            "not_triggered_total": 1,
            "wins": 1,
            "losses": 0,
            "win_rate": 1.0,
            "average_realized_r": 1.5,
            "expectancy_r": 1.5,
        }
    }
