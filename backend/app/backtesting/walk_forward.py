from datetime import datetime, timezone

from app.backtesting.outcomes import label_recommendation_outcome
from app.paper_trading.validation import validate_paper_recommendations
from app.scanner.service import build_features, select_best_catalyst
from app.recommendations.service import build_recommendation


def run_walk_forward_replay(
    ticker,
    candles,
    catalysts=None,
    market_context=None,
    market_context_by_timestamp=None,
    lookback_bars=20,
    horizon_bars=5,
    recommendation_repository=None,
    catalyst_max_age_minutes=None,
    actionable_score_threshold=70,
    include_paper_validation=False,
    paper_account_equity=100_000,
    paper_risk_fraction=0.01,
):
    catalysts = catalysts or []
    market_context = market_context or {"risk_context": "mixed", "spy_trend": "neutral", "qqq_trend": "neutral"}
    sorted_candles = sorted(candles, key=lambda candle: candle.get("timestamp_ms") or 0)
    items = []
    paper_validation_inputs = []
    persisted = 0

    for index in range(lookback_bars, len(sorted_candles)):
        current = sorted_candles[index]
        current_timestamp = current.get("timestamp_ms")
        lookback = sorted_candles[index - lookback_bars : index]
        visible_candles = [*lookback, current]
        future_candles = sorted_candles[index + 1 : index + 1 + horizon_bars]

        decision_market_context = _market_context_for_timestamp(
            current_timestamp,
            market_context,
            market_context_by_timestamp,
        )
        recommendation = _build_historical_recommendation(
            ticker=ticker,
            current_candle=current,
            visible_candles=visible_candles,
            visible_catalysts=_visible_catalysts(catalysts, current_timestamp, catalyst_max_age_minutes),
            market_context=decision_market_context,
            actionable_score_threshold=actionable_score_threshold,
        )
        outcome = label_recommendation_outcome(
            recommendation,
            future_candles,
            recommendation_timestamp_ms=current_timestamp,
        )
        item = {
            "timestamp_ms": current_timestamp,
            "recommendation": recommendation,
            "outcome": outcome,
        }
        if recommendation_repository is not None:
            record = recommendation_repository.save_recommendation(
                recommendation,
                created_at=_datetime_from_timestamp_ms(current_timestamp),
            )
            recommendation_repository.save_outcome(record.id, outcome)
            persisted += 1
        if include_paper_validation:
            paper_validation_inputs.append({"recommendation": recommendation, "candles": future_candles})
        items.append(item)

    result = {
        "ticker": ticker,
        "evaluated_bars": len(items),
        "lookback_bars": lookback_bars,
        "horizon_bars": horizon_bars,
        "persisted_recommendations": persisted,
        "items": items,
        "summary": _summarize_items(items),
    }
    if include_paper_validation:
        result["paper_validation"] = validate_paper_recommendations(
            paper_validation_inputs,
            account_equity=paper_account_equity,
            risk_fraction=paper_risk_fraction,
        )
    return result


def _build_historical_recommendation(
    ticker,
    current_candle,
    visible_candles,
    visible_catalysts,
    market_context,
    actionable_score_threshold=70,
):
    snapshot = _snapshot_from_candle(ticker, current_candle, previous_close=visible_candles[-2].get("close"))
    features = build_features(snapshot, visible_candles, visible_candles[-2:] if len(visible_candles) >= 2 else visible_candles)
    catalyst = select_best_catalyst(_normalized_historical_catalysts(visible_catalysts, current_candle.get("timestamp_ms")))
    recommendation = build_recommendation(
        ticker,
        features,
        catalyst,
        market_context,
        actionable_score_threshold=actionable_score_threshold,
    )
    recommendation["inputs"]["snapshot"] = snapshot
    recommendation["inputs"]["walk_forward"] = {
        "current_timestamp_ms": current_candle.get("timestamp_ms"),
        "visible_candle_count": len(visible_candles),
    }
    return recommendation


def _market_context_for_timestamp(timestamp_ms, default_context, market_context_by_timestamp):
    if not market_context_by_timestamp or timestamp_ms is None:
        return default_context
    eligible_timestamps = [int(ts) for ts in market_context_by_timestamp if int(ts) <= timestamp_ms]
    if not eligible_timestamps:
        return default_context
    return market_context_by_timestamp[max(eligible_timestamps)]


def _snapshot_from_candle(ticker, candle, previous_close):
    close = candle.get("close")
    return {
        "ticker": ticker,
        "provider": "walk_forward_replay",
        "price": close,
        "volume": candle.get("volume"),
        "previous_close": previous_close,
        "bid": round(close * 0.999, 4) if close is not None else None,
        "ask": round(close * 1.001, 4) if close is not None else None,
        "raw": candle,
    }


def _visible_catalysts(catalysts, timestamp_ms, catalyst_max_age_minutes=None):
    if timestamp_ms is None:
        return catalysts
    visible = []
    max_age_ms = catalyst_max_age_minutes * 60_000 if catalyst_max_age_minutes is not None else None
    for catalyst in catalysts:
        catalyst_timestamp = catalyst.get("timestamp_ms")
        if catalyst_timestamp is None:
            visible.append(catalyst)
            continue
        if catalyst_timestamp > timestamp_ms:
            continue
        if max_age_ms is not None and timestamp_ms - catalyst_timestamp > max_age_ms:
            continue
        visible.append(catalyst)
    return visible


def _normalized_historical_catalysts(catalysts, current_timestamp_ms):
    normalized = []
    for catalyst in catalysts:
        item = dict(catalyst)
        item["catalyst_type"] = item.get("catalyst_type") or item.get("type") or "unknown"
        if "event_age_minutes" not in item and item.get("timestamp_ms") is not None and current_timestamp_ms is not None:
            item["event_age_minutes"] = max(round((current_timestamp_ms - item["timestamp_ms"]) / 60_000), 0)
        normalized.append(item)
    return normalized


def _summarize_items(items):
    outcomes = [item["outcome"] for item in items]
    closed = [outcome for outcome in outcomes if outcome.get("status") == "closed"]
    realized = [outcome["realized_r"] for outcome in closed if outcome.get("realized_r") is not None]
    wins = sum(1 for outcome in closed if outcome.get("target_hit"))
    losses = sum(1 for outcome in closed if outcome.get("stop_hit"))
    return {
        "evaluated_total": len(items),
        "closed_total": len(closed),
        "wins": wins,
        "losses": losses,
        "win_rate": _safe_rate(wins, len(closed)),
        "average_realized_r": _average(realized),
        "expectancy_r": _average(realized),
    }


def _datetime_from_timestamp_ms(timestamp_ms):
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def _average(values):
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _safe_rate(numerator, denominator):
    if denominator == 0:
        return None
    return round(numerator / denominator, 2)
