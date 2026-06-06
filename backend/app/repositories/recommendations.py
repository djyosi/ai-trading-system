from app.models.outcome import OutcomeRecord
from app.models.recommendation import RecommendationRecord


class RecommendationRepository:
    def __init__(self, db):
        self.db = db

    def save_recommendation(self, recommendation, created_at=None):
        record = RecommendationRecord(
            ticker=recommendation["ticker"],
            timeframe=recommendation["timeframe"],
            direction=recommendation["direction"],
            status=recommendation["status"],
            setup_score=recommendation["setup_score"],
            confidence=recommendation["confidence"],
            strategy=recommendation["strategy"],
            entry_trigger=recommendation["entry_trigger"],
            entry_zone=recommendation.get("entry_zone"),
            stop_loss=recommendation.get("stop_loss"),
            targets=recommendation.get("targets", []),
            risk_reward=recommendation.get("risk_reward"),
            invalid_if=recommendation.get("invalid_if", []),
            reject_reasons=recommendation.get("reject_reasons", []),
            warnings=recommendation.get("warnings", []),
            reason=recommendation["reason"],
            input_snapshot=recommendation["inputs"],
        )
        if created_at is not None:
            record.created_at = created_at
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_recommendations(self, limit=100):
        return (
            self.db.query(RecommendationRecord)
            .order_by(RecommendationRecord.created_at.desc(), RecommendationRecord.id.desc())
            .limit(limit)
            .all()
        )

    def save_outcome(self, recommendation_id, outcome):
        record = OutcomeRecord(
            recommendation_id=recommendation_id,
            status=outcome["status"],
            max_favorable_excursion_r=outcome.get("max_favorable_excursion_r"),
            max_adverse_excursion_r=outcome.get("max_adverse_excursion_r"),
            realized_r=outcome.get("realized_r"),
            target_hit=outcome.get("target_hit", False),
            stop_hit=outcome.get("stop_hit", False),
            bars_to_target=outcome.get("bars_to_target"),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
