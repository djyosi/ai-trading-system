from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.paper_trading.validation import validate_paper_recommendations

router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])


class PaperValidationItem(BaseModel):
    recommendation: dict[str, Any] = Field(default_factory=dict)
    candles: list[dict[str, Any]] = Field(default_factory=list)


class PaperValidationRequest(BaseModel):
    items: list[PaperValidationItem] = Field(default_factory=list)
    account_equity: int = Field(default=100_000, gt=0)
    risk_fraction: float = Field(default=0.01, gt=0)


@router.post("/validate")
def validate_paper_trading_payload(request: PaperValidationRequest):
    result = validate_paper_recommendations(
        [item.model_dump() for item in request.items],
        account_equity=request.account_equity,
        risk_fraction=request.risk_fraction,
    )
    return {
        "mode": "paper_simulation",
        "orders_enabled": False,
        "data_source": "request_payload",
        **result,
    }
