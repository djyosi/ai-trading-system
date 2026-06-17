from app.jobs.daily_research_policy import evaluate_promotion_gate


def test_promotion_gate_blocks_negative_evidence_backed_expectancy():
    diagnostics_summary = {
        "phase_3_readiness_status": "needs_loss_driver_diagnostics",
        "evidence_vs_baseline_delta_r": -0.33,
        "evidence_backed_expectancy_r": -0.22,
        "baseline_expectancy_r": 0.11,
        "worst_loss_drivers": [],
        "next_research_actions": [],
        "warnings": [],
    }

    result = evaluate_promotion_gate(diagnostics_summary)

    assert result == {
        "promotion_status": "blocked",
        "reason": "evidence_backed_underperformed_baseline",
        "orders_enabled": False,
        "requires_backtest_confirmation": True,
    }


def test_promotion_gate_blocks_insufficient_sample():
    diagnostics_summary = {
        "phase_3_readiness_status": "paper_validation_started",
        "evidence_vs_baseline_delta_r": None,
        "evidence_backed_expectancy_r": None,
        "baseline_expectancy_r": 0.1,
        "worst_loss_drivers": [],
        "next_research_actions": [{"action": "increase_sample_size"}],
        "warnings": [],
    }

    result = evaluate_promotion_gate(diagnostics_summary)

    assert result == {
        "promotion_status": "needs_more_data",
        "reason": "insufficient_evidence_sample",
        "orders_enabled": False,
        "requires_backtest_confirmation": True,
    }


def test_promotion_gate_blocks_when_evidence_does_not_beat_baseline():
    diagnostics_summary = {
        "phase_3_readiness_status": "needs_loss_driver_diagnostics",
        "evidence_vs_baseline_delta_r": 0.0,
        "evidence_backed_expectancy_r": 0.05,
        "baseline_expectancy_r": 0.05,
        "worst_loss_drivers": [],
        "next_research_actions": [],
        "warnings": [],
    }

    result = evaluate_promotion_gate(diagnostics_summary)

    assert result == {
        "promotion_status": "blocked",
        "reason": "evidence_does_not_beat_baseline",
        "orders_enabled": False,
        "requires_backtest_confirmation": True,
    }


def test_promotion_gate_promotes_candidate_after_positive_evidence():
    diagnostics_summary = {
        "phase_3_readiness_status": "paper_validation_started",
        "evidence_vs_baseline_delta_r": 0.4,
        "evidence_backed_expectancy_r": 0.5,
        "baseline_expectancy_r": 0.1,
        "worst_loss_drivers": [],
        "next_research_actions": [],
        "warnings": [],
    }

    result = evaluate_promotion_gate(diagnostics_summary)

    assert result == {
        "promotion_status": "candidate_for_backtest_confirmation",
        "reason": "evidence_backed_outperformed_baseline",
        "orders_enabled": False,
        "requires_backtest_confirmation": True,
        "evidence_backed_expectancy_r": 0.5,
        "evidence_vs_baseline_delta_r": 0.4,
    }
