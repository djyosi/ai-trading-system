from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recommendation import RecommendationRecord
from app.repositories.recommendations import RecommendationRepository

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
def list_recommendations(limit: int = 100, db: Session = Depends(get_db)):
    repo = RecommendationRepository(db)
    records = repo.list_recommendations(limit=limit)
    return {"items": [_serialize_recommendation(record) for record in records]}


@router.get("/{recommendation_id}")
def get_recommendation(recommendation_id: int, db: Session = Depends(get_db)):
    record = db.get(RecommendationRecord, recommendation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return _serialize_recommendation(record)


def _serialize_recommendation(record):
    return {
        "id": record.id,
        "ticker": record.ticker,
        "timeframe": record.timeframe,
        "direction": record.direction,
        "status": record.status,
        "setup_score": record.setup_score,
        "confidence": record.confidence,
        "strategy": record.strategy,
        "strategy_segment": record.strategy_segment,
        "research_tags": record.research_tags,
        "research_evidence": record.research_evidence,
        "entry_trigger": record.entry_trigger,
        "entry_zone": record.entry_zone,
        "stop_loss": record.stop_loss,
        "targets": record.targets,
        "risk_reward": record.risk_reward,
        "invalid_if": record.invalid_if,
        "reject_reasons": record.reject_reasons,
        "warnings": record.warnings,
        "reason": record.reason,
        "input_snapshot": record.input_snapshot,
        "created_at": record.created_at.isoformat(),
    }
