RECOMMENDATION_STATUSES = {"active_watch", "caution", "no_trade"}
RECOMMENDATION_TIMEFRAMES = {"day_trade", "swing_trade"}


def is_actionable_recommendation(recommendation):
    return recommendation.get("status") in {"active_watch", "caution"}
