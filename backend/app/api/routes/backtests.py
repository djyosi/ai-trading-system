from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.backtesting.batch import run_historical_batch
from app.backtesting.threshold_sweep import sweep_score_thresholds, tune_thresholds_by_segment
from app.backtesting.walk_forward import run_walk_forward_replay
from app.db.session import get_db
from app.providers.massive import MassiveProvider
from app.repositories.recommendations import RecommendationRepository

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
    thresholds: list[int] = Field(default_factory=lambda: [50, 60, 70, 80, 85, 90])
    min_trades: int = Field(default=1, ge=1)


class BatchBacktestRequest(BaseModel):
    tickers: list[str] = Field(min_length=1)
    start: str
    end: str
    catalysts_by_ticker: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    market_context: dict[str, Any] = Field(default_factory=dict)
    lookback_bars: int = Field(default=20, ge=1)
    horizon_bars: int = Field(default=5, ge=1)


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
    return await run_historical_batch(
        tickers=[ticker.upper() for ticker in request.tickers],
        market_data_provider=market_data_provider,
        start=request.start,
        end=request.end,
        catalysts_by_ticker=request.catalysts_by_ticker,
        market_context=request.market_context,
        lookback_bars=request.lookback_bars,
        horizon_bars=request.horizon_bars,
    )


async def _resolve_candles(request, market_data_provider):
    if request.source is None or request.source == "request_payload":
        return request.candles
    if request.source != "massive":
        raise HTTPException(status_code=400, detail="Unsupported backtest source")
    if not request.start or not request.end:
        raise HTTPException(status_code=400, detail="start and end are required when source is massive")
    return await market_data_provider.get_daily_candles(request.ticker, request.start, request.end)
