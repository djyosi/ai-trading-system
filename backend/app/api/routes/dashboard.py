from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.research_evidence import rank_components, rank_evidence_policy, rank_evidence_status, rank_reasons, rank_score
from app.db.session import get_db
from app.models.recommendation import RecommendationRecord

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/ranked-recommendations")
def ranked_recommendations(limit: int = 25, db: Session = Depends(get_db)):
    records = db.query(RecommendationRecord).filter(RecommendationRecord.status != "no_trade").all()
    records = sorted(
        records,
        key=lambda record: (_rank_score(record), record.created_at, record.id),
        reverse=True,
    )[:limit]
    items = [_ranked_item(rank, record) for rank, record in enumerate(records, start=1)]
    return {"items_total": len(items), "rank_policy": rank_evidence_policy(), "items": items}


def _rank_evidence(record):
    return rank_evidence_status(record)


def _rank_components(record):
    return rank_components(record)


def _rank_reasons(record):
    return rank_reasons(record)


def _rank_score(record):
    return rank_score(record)


def _ranked_item(rank, record):
    catalyst = (record.input_snapshot or {}).get("catalyst") or {}
    features = (record.input_snapshot or {}).get("features") or {}
    return {
        "rank": rank,
        "id": record.id,
        "ticker": record.ticker,
        "status": record.status,
        "setup_score": record.setup_score,
        "rank_score": _rank_score(record),
        "rank_components": _rank_components(record),
        "rank_reasons": _rank_reasons(record),
        "rank_evidence": _rank_evidence(record),
        "confidence": record.confidence,
        "strategy": record.strategy,
        "strategy_segment": record.strategy_segment,
        "research_tags": record.research_tags,
        "research_evidence": record.research_evidence,
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
