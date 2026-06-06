from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.providers.massive import MassiveProvider
from app.repositories.recommendations import RecommendationRepository
from app.scanner.service import ScannerService

router = APIRouter(tags=["scanner"])


class ScanRequest(BaseModel):
    tickers: list[str]


class NoopCatalystProvider:
    async def get_catalysts(self, ticker):
        return []


class StaticMarketContextProvider:
    async def get_market_context(self):
        return {
            "spy_trend": "neutral",
            "qqq_trend": "neutral",
            "iwm_trend": "neutral",
            "risk_context": "mixed",
        }


def get_scanner_service(db: Session = Depends(get_db)):
    return ScannerService(
        market_data_provider=MassiveProvider(),
        catalyst_provider=NoopCatalystProvider(),
        market_context_provider=StaticMarketContextProvider(),
        recommendation_repository=RecommendationRepository(db),
    )


@router.post("/scan")
async def scan(request: ScanRequest, scanner_service: ScannerService = Depends(get_scanner_service)):
    tickers = [ticker.strip().upper() for ticker in request.tickers if ticker.strip()]
    if not tickers:
        raise HTTPException(status_code=400, detail="At least one ticker is required")
    return {"items": await scanner_service.scan(tickers)}
