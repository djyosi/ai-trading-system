MIN_EVIDENCE_SAMPLE_FOR_PROMOTION = 10


def evaluate_promotion_gate(diagnostics_summary):
    ds = diagnostics_summary or {}
    evidence_expectancy = ds.get("evidence_backed_expectancy_r")
    delta = ds.get("evidence_vs_baseline_delta_r")

    if evidence_expectancy is None or delta is None:
        return {
            "promotion_status": "needs_more_data",
            "reason": "insufficient_evidence_sample",
            "orders_enabled": False,
            "requires_backtest_confirmation": True,
        }

    if evidence_expectancy <= 0:
        return {
            "promotion_status": "blocked",
            "reason": "evidence_backed_underperformed_baseline",
            "orders_enabled": False,
            "requires_backtest_confirmation": True,
        }

    if delta <= 0:
        return {
            "promotion_status": "blocked",
            "reason": "evidence_does_not_beat_baseline",
            "orders_enabled": False,
            "requires_backtest_confirmation": True,
        }

    return {
        "promotion_status": "candidate_for_backtest_confirmation",
        "reason": "evidence_backed_outperformed_baseline",
        "orders_enabled": False,
        "requires_backtest_confirmation": True,
        "evidence_backed_expectancy_r": evidence_expectancy,
        "evidence_vs_baseline_delta_r": delta,
    }
