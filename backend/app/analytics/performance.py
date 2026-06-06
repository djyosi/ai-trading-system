from app.models.outcome import OutcomeRecord
from app.models.recommendation import RecommendationRecord


def summarize_performance(db):
    recommendations = db.query(RecommendationRecord).all()
    joined = (
        db.query(RecommendationRecord, OutcomeRecord)
        .join(OutcomeRecord, OutcomeRecord.recommendation_id == RecommendationRecord.id)
        .all()
    )
    closed = [(recommendation, outcome) for recommendation, outcome in joined if outcome.status == "closed"]
    realized_values = [outcome.realized_r for _, outcome in closed if outcome.realized_r is not None]
    wins = sum(1 for _, outcome in closed if outcome.target_hit or (outcome.realized_r is not None and outcome.realized_r > 0))
    losses = sum(1 for _, outcome in closed if outcome.stop_hit or (outcome.realized_r is not None and outcome.realized_r < 0))

    return {
        "recommendations_total": len(recommendations),
        "actionable_total": sum(1 for item in recommendations if item.status != "no_trade"),
        "closed_total": len(closed),
        "wins": wins,
        "losses": losses,
        "win_rate": _safe_rate(wins, len(closed)),
        "average_realized_r": _average(realized_values),
        "expectancy_r": _average(realized_values),
        "no_trade_total": sum(1 for item in recommendations if item.status == "no_trade"),
        "by_strategy": _group_metrics(closed, lambda recommendation: recommendation.strategy),
        "by_catalyst_type": _group_metrics(
            closed,
            lambda recommendation: (recommendation.input_snapshot.get("catalyst") or {}).get("catalyst_type", "unknown"),
        ),
        "by_score_band": _group_metrics(closed, lambda recommendation: _score_band(recommendation.setup_score)),
    }


def _group_metrics(closed, key_fn):
    grouped = {}
    for recommendation, outcome in closed:
        key = key_fn(recommendation)
        grouped.setdefault(key, []).append(outcome)

    return {key: _metrics_for_outcomes(outcomes) for key, outcomes in sorted(grouped.items())}


def _metrics_for_outcomes(outcomes):
    realized_values = [outcome.realized_r for outcome in outcomes if outcome.realized_r is not None]
    wins = sum(1 for outcome in outcomes if outcome.target_hit or (outcome.realized_r is not None and outcome.realized_r > 0))
    return {
        "closed_total": len(outcomes),
        "wins": wins,
        "win_rate": _safe_rate(wins, len(outcomes)),
        "average_realized_r": _average(realized_values),
        "expectancy_r": _average(realized_values),
    }


def _score_band(score):
    if score is None:
        return "unknown"
    if score >= 85:
        return "85-100"
    if score >= 70:
        return "70-84"
    if score >= 60:
        return "60-69"
    if score >= 40:
        return "40-59"
    return "0-39"


def _average(values):
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _safe_rate(numerator, denominator):
    if denominator == 0:
        return None
    return round(numerator / denominator, 2)
