MIN_EVIDENCE_TRADES_FOR_RANK_BOOST = 10


def rank_evidence_status(recommendation):
    evidence = recommendation.research_evidence or {}
    tagged = "market_context_edge_candidate" in (recommendation.research_tags or [])
    expectancy_r = evidence.get("expectancy_r")
    trade_count = evidence.get("trade_count")
    status = "eligible"
    if not tagged:
        status = "not_tagged"
    elif (expectancy_r or 0) <= 0:
        status = "non_positive_expectancy"
    elif (trade_count or 0) < MIN_EVIDENCE_TRADES_FOR_RANK_BOOST:
        status = "insufficient_sample"

    return {
        "market_context_boost_eligible": status == "eligible",
        "market_context_boost_status": status,
        "market_context_segment": evidence.get("market_context_segment"),
        "expectancy_r": expectancy_r,
        "trade_count": trade_count,
        "min_trade_count": MIN_EVIDENCE_TRADES_FOR_RANK_BOOST,
    }
