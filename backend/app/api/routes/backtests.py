from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.backtesting.walk_forward import run_walk_forward_replay

router = APIRouter(prefix="/backtests", tags=["backtests"])


class WalkForwardReplayRequest(BaseModel):
    ticker: str
    candles: list[dict[str, Any]] = Field(default_factory=list)
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    market_context: dict[str, Any] = Field(default_factory=dict)
    lookback_bars: int = Field(default=20, ge=1)
    horizon_bars: int = Field(default=5, ge=1)


@router.post("/walk-forward")
def run_walk_forward_backtest(request: WalkForwardReplayRequest):
    if len(request.candles) <= request.lookback_bars:
        raise HTTPException(status_code=400, detail="Not enough candles for requested lookback")
    return run_walk_forward_replay(
        ticker=request.ticker,
        candles=request.candles,
        catalysts=request.catalysts,
        market_context=request.market_context,
        lookback_bars=request.lookback_bars,
        horizon_bars=request.horizon_bars,
    )
