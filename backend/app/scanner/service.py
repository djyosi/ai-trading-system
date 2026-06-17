from datetime import datetime, timedelta, timezone

from app.catalysts.classifier import calculate_freshness, classify_catalyst
from app.features.chart_patterns import classify_candle_pattern, classify_multi_candle_pattern
from app.features.liquidity import (
    calculate_dollar_volume,
    calculate_liquidity_score,
    calculate_relative_volume,
    calculate_spread_percent,
)
from app.features.technicals import (
    calculate_atr_percent,
    calculate_gap_percent,
    calculate_opening_range,
    calculate_prior_levels,
    calculate_vwap,
)
from app.recommendations.service import build_recommendation


class ScannerService:
    def __init__(
        self,
        market_data_provider,
        catalyst_provider,
        market_context_provider,
        recommendation_repository=None,
    ):
        self.market_data_provider = market_data_provider
        self.catalyst_provider = catalyst_provider
        self.market_context_provider = market_context_provider
        self.recommendation_repository = recommendation_repository

    async def scan(self, tickers):
        market_context = await self.market_context_provider.get_market_context()
        results = []
        for ticker in tickers:
            try:
                recommendation = await self._scan_one(ticker, market_context)
            except Exception as exc:  # noqa: BLE001 - scanner must continue per-symbol
                results.append({"ticker": ticker, "status": "error", "error": str(exc)})
                continue
            if self.recommendation_repository is not None:
                self.recommendation_repository.save_recommendation(recommendation)
            results.append(recommendation)
        return results

    async def _scan_one(self, ticker, market_context):
        ranges = _default_scan_ranges()
        snapshot = await self.market_data_provider.get_snapshot(ticker)
        daily_candles = await self.market_data_provider.get_daily_candles(
            ticker,
            start=ranges["daily_start"],
            end=ranges["daily_end"],
        )
        intraday_candles = await self.market_data_provider.get_intraday_candles(
            ticker,
            start=ranges["intraday_start"],
            end=ranges["intraday_end"],
            timeframe="1m",
        )
        catalysts = await self.catalyst_provider.get_catalysts(ticker)

        features = build_features(snapshot, daily_candles, intraday_candles)
        catalyst = select_best_catalyst(catalysts)
        recommendation = build_recommendation(ticker, features, catalyst, market_context)
        recommendation["inputs"]["snapshot"] = snapshot
        return recommendation


def build_features(snapshot, daily_candles, intraday_candles):
    current_price = snapshot.get("price")
    volume = snapshot.get("volume")
    average_volume = _average_volume(daily_candles)
    opening_range = calculate_opening_range(intraday_candles)
    prior_levels = calculate_prior_levels(daily_candles)
    chart_pattern = {"pattern": "none", "direction": "neutral", "strength": "none"}
    if intraday_candles:
        chart_pattern = classify_candle_pattern(intraday_candles[-1])
        if len(intraday_candles) >= 2 and chart_pattern["pattern"] == "none":
            multi = classify_multi_candle_pattern(intraday_candles[-2], intraday_candles[-1])
            if multi["pattern"] != "none":
                chart_pattern = multi

    return {
        "price": current_price,
        "current_price": current_price,
        "previous_close": snapshot.get("previous_close"),
        "volume": volume,
        "average_volume": average_volume,
        "gap_percent": calculate_gap_percent(snapshot.get("previous_close"), current_price),
        "vwap": calculate_vwap(intraday_candles),
        "atr_percent": calculate_atr_percent(daily_candles),
        "dollar_volume": calculate_dollar_volume(current_price, volume),
        "spread_percent": calculate_spread_percent(snapshot.get("bid"), snapshot.get("ask")),
        "relative_volume": calculate_relative_volume(volume, average_volume),
        "liquidity_score": calculate_liquidity_score(
            current_price,
            volume,
            average_volume,
            bid=snapshot.get("bid"),
            ask=snapshot.get("ask"),
        ),
        **opening_range,
        **prior_levels,
        "chart_pattern": chart_pattern,
    }


def select_best_catalyst(catalysts):
    if not catalysts:
        return {"catalyst_type": "unknown", "signal": "neutral", "strength": "weak", "score": 0, "freshness": "stale"}

    classified = []
    for catalyst in catalysts:
        normalized = classify_catalyst(catalyst)
        age_minutes = catalyst.get("event_age_minutes", 999999)
        normalized["freshness"] = calculate_freshness(age_minutes)
        normalized["summary"] = catalyst.get("summary")
        classified.append(normalized)
    return max(classified, key=lambda item: item["score"])


def _average_volume(candles):
    volumes = [candle.get("volume") for candle in candles if candle.get("volume") is not None]
    if not volumes:
        return None
    return round(sum(volumes) / len(volumes))


def _default_scan_ranges(now=None):
    current = now or datetime.now(timezone.utc)
    end = current.date()
    return {
        "daily_start": end - timedelta(days=30),
        "daily_end": end,
        "intraday_start": end,
        "intraday_end": end,
    }
