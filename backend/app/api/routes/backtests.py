from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.backtesting.walk_forward import run_walk_forward_replay
from app.providers.massive import MassiveProvider

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


def get_backtest_market_data_provider():
    return MassiveProvider()


@router.post("/walk-forward")
async def run_walk_forward_backtest(
    request: WalkForwardReplayRequest,
    market_data_provider=Depends(get_backtest_market_data_provider),
):
    candles = await _resolve_candles(request, market_data_provider)
    if len(candles) <= request.lookback_bars:
        raise HTTPException(status_code=400, detail="Not enough candles for requested lookback")
    result = run_walk_forward_replay(
        ticker=request.ticker,
        candles=candles,
        catalysts=request.catalysts,
        market_context=request.market_context,
        lookback_bars=request.lookback_bars,
        horizon_bars=request.horizon_bars,
    )
    result["data_source"] = request.source or "request_payload"
    result["source_candle_count"] = len(candles)
    return result


async def _resolve_candles(request, market_data_provider):
    if request.source is None or request.source == "request_payload":
        return request.candles
    if request.source != "massive":
        raise HTTPException(status_code=400, detail="Unsupported backtest source")
    if not request.start or not request.end:
        raise HTTPException(status_code=400, detail="start and end are required when source is massive")
    return await market_data_provider.get_daily_candles(request.ticker, request.start, request.end)
