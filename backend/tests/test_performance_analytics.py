from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.analytics.performance import summarize_performance
from app.db.base import Base
from app.repositories.recommendations import RecommendationRepository


def _repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return RecommendationRepository(sessionmaker(bind=engine)())


def _recommendation(
    ticker,
    strategy,
    catalyst_type,
    status="active_watch",
    setup_score=80,
    research_tags=None,
    research_evidence=None,
):
    return {
        "ticker": ticker,
        "timeframe": "day_trade",
        "direction": "long",
        "status": status,
        "setup_score": setup_score,
        "confidence": "medium_high",
        "strategy": strategy,
        "strategy_segment": f"{strategy}|{catalyst_type}",
        "research_tags": research_tags or [],
        "research_evidence": research_evidence or {},
        "entry_trigger": "breakout",
        "entry_zone": [10.0, 10.2],
        "stop_loss": 9.7,
        "targets": [10.8, 11.4],
        "risk_reward": 2.0,
        "invalid_if": ["loses VWAP"],
        "reject_reasons": [] if status != "no_trade" else ["liquidity_score_below_min"],
        "warnings": [],
        "reason": "test recommendation",
        "inputs": {
            "features": {"relative_volume": 3.1, "liquidity_score": 90},
            "catalyst": {"catalyst_type": catalyst_type},
            "market_context": {"risk_context": "supportive"},
        },
    }


def test_summarize_performance_returns_overall_metrics():
    repo = _repo()
    winner = repo.save_recommendation(_recommendation("AAA", "gap_and_go", "earnings_beat"))
    loser = repo.save_recommendation(_recommendation("BBB", "gap_and_go", "earnings_beat"))
    open_trade = repo.save_recommendation(_recommendation("CCC", "vwap_hold", "unknown"))
    no_trade = repo.save_recommendation(_recommendation("DDD", "none", "unknown", status="no_trade", setup_score=0))
    repo.save_outcome(winner.id, {"status": "closed", "realized_r": 2.0, "target_hit": True, "stop_hit": False})
    repo.save_outcome(loser.id, {"status": "closed", "realized_r": -1.0, "target_hit": False, "stop_hit": True})
    repo.save_outcome(open_trade.id, {"status": "open", "realized_r": None, "target_hit": False, "stop_hit": False})
    repo.save_outcome(no_trade.id, {"status": "skipped", "realized_r": None, "target_hit": False, "stop_hit": False})

    summary = summarize_performance(repo.db)

    assert summary["recommendations_total"] == 4
    assert summary["actionable_total"] == 3
    assert summary["closed_total"] == 2
    assert summary["wins"] == 1
    assert summary["losses"] == 1
    assert summary["win_rate"] == 0.5
    assert summary["average_realized_r"] == 0.5
    assert summary["expectancy_r"] == 0.5
    assert summary["no_trade_total"] == 1
    assert summary["rank_evidence_policy"] == {
        "market_context_evidence_boost": 5,
        "min_evidence_trades_for_rank_boost": 10,
        "requires_positive_expectancy": True,
    }


def test_summarize_performance_groups_by_strategy_and_catalyst():
    repo = _repo()
    first = repo.save_recommendation(_recommendation("AAA", "gap_and_go", "earnings_beat"))
    second = repo.save_recommendation(_recommendation("BBB", "gap_and_go", "insider_director_purchase"))
    third = repo.save_recommendation(_recommendation("CCC", "vwap_hold", "earnings_beat"))
    repo.save_outcome(first.id, {"status": "closed", "realized_r": 1.5, "target_hit": True, "stop_hit": False})
    repo.save_outcome(second.id, {"status": "closed", "realized_r": -1.0, "target_hit": False, "stop_hit": True})
    repo.save_outcome(third.id, {"status": "closed", "realized_r": 0.5, "target_hit": True, "stop_hit": False})

    summary = summarize_performance(repo.db)

    assert summary["by_strategy"] == {
        "gap_and_go": {
            "closed_total": 2,
            "wins": 1,
            "win_rate": 0.5,
            "average_realized_r": 0.25,
            "expectancy_r": 0.25,
        },
        "vwap_hold": {
            "closed_total": 1,
            "wins": 1,
            "win_rate": 1.0,
            "average_realized_r": 0.5,
            "expectancy_r": 0.5,
        },
    }
    assert summary["by_catalyst_type"]["earnings_beat"]["closed_total"] == 2
    assert summary["by_catalyst_type"]["earnings_beat"]["average_realized_r"] == 1.0
    assert summary["by_catalyst_type"]["insider_director_purchase"]["average_realized_r"] == -1.0


def test_summarize_performance_groups_by_score_band_for_threshold_tuning():
    repo = _repo()
    high = repo.save_recommendation(_recommendation("AAA", "gap_and_go", "earnings_beat", setup_score=91))
    medium = repo.save_recommendation(_recommendation("BBB", "gap_and_go", "earnings_beat", setup_score=72))
    low = repo.save_recommendation(_recommendation("CCC", "gap_and_go", "earnings_beat", setup_score=41))
    repo.save_outcome(high.id, {"status": "closed", "realized_r": 2.0, "target_hit": True, "stop_hit": False})
    repo.save_outcome(medium.id, {"status": "closed", "realized_r": -1.0, "target_hit": False, "stop_hit": True})
    repo.save_outcome(low.id, {"status": "closed", "realized_r": -0.5, "target_hit": False, "stop_hit": True})

    summary = summarize_performance(repo.db)

    assert summary["by_score_band"] == {
        "40-59": {"closed_total": 1, "wins": 0, "win_rate": 0.0, "average_realized_r": -0.5, "expectancy_r": -0.5},
        "70-84": {"closed_total": 1, "wins": 0, "win_rate": 0.0, "average_realized_r": -1.0, "expectancy_r": -1.0},
        "85-100": {"closed_total": 1, "wins": 1, "win_rate": 1.0, "average_realized_r": 2.0, "expectancy_r": 2.0},
    }


def test_summarize_performance_groups_by_research_evidence_for_learning():
    repo = _repo()
    evidence = {
        "market_context_segment": "vwap_hold_reclaim|contract_win|supportive",
        "recommended_threshold": 60,
        "trade_count": 74,
        "win_rate": 0.45,
        "expectancy_r": 0.11,
    }
    supported_winner = repo.save_recommendation(
        _recommendation(
            "AAA",
            "vwap_hold_reclaim",
            "contract_win",
            research_tags=["segment_edge_candidate", "market_context_edge_candidate"],
            research_evidence=evidence,
        )
    )
    unsupported_loser = repo.save_recommendation(_recommendation("BBB", "gap_and_go", "unknown"))
    repo.save_outcome(supported_winner.id, {"status": "closed", "realized_r": 1.5, "target_hit": True, "stop_hit": False})
    repo.save_outcome(unsupported_loser.id, {"status": "closed", "realized_r": -1.0, "target_hit": False, "stop_hit": True})

    summary = summarize_performance(repo.db)

    assert summary["by_research_tag"]["market_context_edge_candidate"] == {
        "closed_total": 1,
        "wins": 1,
        "win_rate": 1.0,
        "average_realized_r": 1.5,
        "expectancy_r": 1.5,
    }
    assert summary["by_research_tag"]["no_research_tag"]["average_realized_r"] == -1.0
    assert summary["by_market_context_segment"]["vwap_hold_reclaim|contract_win|supportive"]["expectancy_r"] == 1.5
    assert summary["by_market_context_segment"]["no_market_context_segment"]["expectancy_r"] == -1.0


def test_summarize_performance_groups_by_rank_evidence_status():
    repo = _repo()
    eligible = repo.save_recommendation(
        _recommendation(
            "AAA",
            "vwap_hold_reclaim",
            "contract_win",
            research_tags=["market_context_edge_candidate"],
            research_evidence={
                "market_context_segment": "vwap_hold_reclaim|contract_win|supportive",
                "trade_count": 18,
                "expectancy_r": 0.22,
            },
        )
    )
    insufficient = repo.save_recommendation(
        _recommendation(
            "BBB",
            "vwap_hold_reclaim",
            "contract_win",
            research_tags=["market_context_edge_candidate"],
            research_evidence={
                "market_context_segment": "vwap_hold_reclaim|contract_win|supportive",
                "trade_count": 4,
                "expectancy_r": 0.8,
            },
        )
    )
    non_positive = repo.save_recommendation(
        _recommendation(
            "CCC",
            "gap_and_go",
            "earnings_beat",
            research_tags=["market_context_edge_candidate"],
            research_evidence={
                "market_context_segment": "gap_and_go|earnings_beat|mixed",
                "trade_count": 25,
                "expectancy_r": 0.0,
            },
        )
    )
    untagged = repo.save_recommendation(_recommendation("DDD", "gap_and_go", "unknown"))
    repo.save_outcome(eligible.id, {"status": "closed", "realized_r": 1.5, "target_hit": True, "stop_hit": False})
    repo.save_outcome(insufficient.id, {"status": "closed", "realized_r": -0.5, "target_hit": False, "stop_hit": True})
    repo.save_outcome(non_positive.id, {"status": "closed", "realized_r": -1.0, "target_hit": False, "stop_hit": True})
    repo.save_outcome(untagged.id, {"status": "closed", "realized_r": 0.25, "target_hit": True, "stop_hit": False})

    summary = summarize_performance(repo.db)

    assert summary["by_rank_evidence_status"]["eligible"]["expectancy_r"] == 1.5
    assert summary["by_rank_evidence_status"]["insufficient_sample"]["expectancy_r"] == -0.5
    assert summary["by_rank_evidence_status"]["non_positive_expectancy"]["expectancy_r"] == -1.0
    assert summary["by_rank_evidence_status"]["not_tagged"]["expectancy_r"] == 0.25


def test_summarize_performance_handles_empty_history():
    repo = _repo()

    summary = summarize_performance(repo.db)

    assert summary["recommendations_total"] == 0
    assert summary["closed_total"] == 0
    assert summary["win_rate"] is None
    assert summary["average_realized_r"] is None
    assert summary["by_strategy"] == {}
