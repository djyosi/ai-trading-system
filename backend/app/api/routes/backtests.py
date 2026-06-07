from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.backtesting.batch import run_historical_batch
from app.backtesting.research_report import build_batch_research_report
from app.backtesting.threshold_sweep import DEFAULT_SCORE_THRESHOLDS, sweep_score_thresholds, tune_thresholds_by_segment
from app.backtesting.walk_forward import run_walk_forward_replay
from app.db.session import get_db
from app.providers.massive import MassiveProvider
from app.repositories.recommendations import RecommendationRepository
from app.universe.presets import resolve_universe_preset

router = APIRouter(prefix="/backtests", tags=["backtests"])


class WalkForwardReplayRequest(BaseModel):
    ticker: str
    candles: list[dict[str, Any]] = Field(default_factory=list)
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    market_context: dict[str, Any] = Field(default_factory=dict)
    lookback_bars: int = Field(default=20, ge=1)
    horizon_bars: int = Field(default=5, ge=1)
    source: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    persist_recommendations: bool = False
    include_threshold_sweep: bool = False
    thresholds: list[int] = Field(default_factory=lambda: list(DEFAULT_SCORE_THRESHOLDS))
    min_trades: int = Field(default=1, ge=1)
    catalyst_max_age_minutes: Optional[int] = Field(default=None, ge=0)
    actionable_score_threshold: int = Field(default=70, ge=0, le=100)


class BatchBacktestRequest(BaseModel):
    tickers: list[str] = Field(default_factory=list)
    universe_preset: Optional[str] = None
    start: str
    end: str
    catalysts_by_ticker: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    market_context: dict[str, Any] = Field(default_factory=dict)
    lookback_bars: int = Field(default=20, ge=1)
    horizon_bars: int = Field(default=5, ge=1)
    include_threshold_sweep: bool = False
    include_research_report: bool = False
    include_news_catalysts: bool = False
    thresholds: list[int] = Field(default_factory=lambda: list(DEFAULT_SCORE_THRESHOLDS))
    min_trades: int = Field(default=1, ge=1)
    catalyst_max_age_minutes: Optional[int] = Field(default=None, ge=0)
    actionable_score_threshold: int = Field(default=70, ge=0, le=100)


def get_backtest_market_data_provider():
    return MassiveProvider()


@router.post("/walk-forward")
async def run_walk_forward_backtest(
    request: WalkForwardReplayRequest,
    market_data_provider=Depends(get_backtest_market_data_provider),
    db=Depends(get_db),
):
    candles = await _resolve_candles(request, market_data_provider)
    if len(candles) <= request.lookback_bars:
        raise HTTPException(status_code=400, detail="Not enough candles for requested lookback")
    repository = RecommendationRepository(db) if request.persist_recommendations else None
    result = run_walk_forward_replay(
        ticker=request.ticker,
        candles=candles,
        catalysts=request.catalysts,
        market_context=request.market_context,
        lookback_bars=request.lookback_bars,
        horizon_bars=request.horizon_bars,
        recommendation_repository=repository,
        catalyst_max_age_minutes=request.catalyst_max_age_minutes,
        actionable_score_threshold=request.actionable_score_threshold,
    )
    result["data_source"] = request.source or "request_payload"
    result["source_candle_count"] = len(candles)
    if request.include_threshold_sweep:
        result["threshold_sweep"] = sweep_score_thresholds(
            result["items"], thresholds=request.thresholds, min_trades=request.min_trades
        )
        result["threshold_tuning_by_segment"] = tune_thresholds_by_segment(
            result["items"], thresholds=request.thresholds, min_trades=request.min_trades
        )
    return result


@router.post("/batch")
async def run_batch_backtest(request: BatchBacktestRequest, market_data_provider=Depends(get_backtest_market_data_provider)):
    try:
        tickers = _resolve_batch_tickers(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    catalysts_by_ticker = dict(request.catalysts_by_ticker)
    news_catalysts_fetched = 0
    if request.include_news_catalysts:
        fetched = await _fetch_news_catalysts(tickers, request.start, request.end, market_data_provider)
        for ticker, catalysts in fetched.items():
            catalysts_by_ticker[ticker] = [*catalysts_by_ticker.get(ticker, []), *catalysts]
            news_catalysts_fetched += len(catalysts)
    result = await run_historical_batch(
        tickers=tickers,
        market_data_provider=market_data_provider,
        start=request.start,
        end=request.end,
        catalysts_by_ticker=catalysts_by_ticker,
        market_context=request.market_context,
        lookback_bars=request.lookback_bars,
        horizon_bars=request.horizon_bars,
        catalyst_max_age_minutes=request.catalyst_max_age_minutes,
        actionable_score_threshold=request.actionable_score_threshold,
    )
    result["news_catalysts_fetched"] = news_catalysts_fetched
    if request.universe_preset:
        result["universe_preset"] = request.universe_preset
    if request.include_threshold_sweep or request.include_research_report:
        items = [item for ticker_result in result["results"].values() for item in ticker_result["items"]]
        result["aggregate_threshold_sweep"] = sweep_score_thresholds(
            items, thresholds=request.thresholds, min_trades=request.min_trades
        )
        result["aggregate_threshold_tuning_by_segment"] = tune_thresholds_by_segment(
            items, thresholds=request.thresholds, min_trades=request.min_trades
        )
    if request.include_research_report:
        result["research_report"] = build_batch_research_report(result)
    return result


def _resolve_batch_tickers(request):
    tickers = [ticker.upper() for ticker in request.tickers]
    if request.universe_preset:
        tickers = [*tickers, *resolve_universe_preset(request.universe_preset)]
    deduped = list(dict.fromkeys(tickers))
    if not deduped:
        raise ValueError("Either tickers or universe_preset is required")
    return deduped


async def _fetch_news_catalysts(tickers, start, end, market_data_provider):
    if not hasattr(market_data_provider, "get_news"):
        raise HTTPException(status_code=400, detail="Configured provider does not support news catalysts")
    return {ticker: await market_data_provider.get_news(ticker, start, end) for ticker in tickers}


async def _resolve_candles(request, market_data_provider):
    if request.source is None or request.source == "request_payload":
        return request.candles
    if request.source != "massive":
        raise HTTPException(status_code=400, detail="Unsupported backtest source")
    if not request.start or not request.end:
        raise HTTPException(status_code=400, detail="start and end are required when source is massive")
    return await market_data_provider.get_daily_candles(request.ticker, request.start, request.end)
