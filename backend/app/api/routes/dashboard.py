from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
    return {"items_total": len(items), "items": items}


def _rank_components(record):
    return {
        "base_setup_score": record.setup_score,
        "market_context_evidence_boost": _market_context_evidence_boost(record),
    }


def _rank_reasons(record):
    if _market_context_evidence_boost(record) == 0:
        return []
    segment = (record.research_evidence or {}).get("market_context_segment", "unknown_segment")
    return [f"market_context_edge_candidate: {segment}"]


def _rank_score(record):
    components = _rank_components(record)
    return components["base_setup_score"] + components["market_context_evidence_boost"]


def _market_context_evidence_boost(record):
    return 5 if "market_context_edge_candidate" in (record.research_tags or []) else 0


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
