from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recommendation import RecommendationRecord

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/ranked-recommendations")
def ranked_recommendations(limit: int = 25, db: Session = Depends(get_db)):
    records = (
        db.query(RecommendationRecord)
        .filter(RecommendationRecord.status != "no_trade")
        .order_by(RecommendationRecord.setup_score.desc(), RecommendationRecord.created_at.desc(), RecommendationRecord.id.desc())
        .limit(limit)
        .all()
    )
    items = [_ranked_item(rank, record) for rank, record in enumerate(records, start=1)]
    return {"items_total": len(items), "items": items}


def _ranked_item(rank, record):
    catalyst = (record.input_snapshot or {}).get("catalyst") or {}
    features = (record.input_snapshot or {}).get("features") or {}
    return {
        "rank": rank,
        "id": record.id,
        "ticker": record.ticker,
        "status": record.status,
        "setup_score": record.setup_score,
        "confidence": record.confidence,
        "strategy": record.strategy,
        "catalyst_type": catalyst.get("catalyst_type", "unknown"),
        "relative_volume": features.get("relative_volume"),
        "entry_trigger": record.entry_trigger,
        "entry_zone": record.entry_zone,
        "stop_loss": record.stop_loss,
        "targets": record.targets,
        "risk_reward": record.risk_reward,
        "reason": record.reason,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
