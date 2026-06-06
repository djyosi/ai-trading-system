from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.recommendation import RecommendationRecord


class OutcomeRecord(Base):
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    max_favorable_excursion_r: Mapped[float] = mapped_column(Float, nullable=True)
    max_adverse_excursion_r: Mapped[float] = mapped_column(Float, nullable=True)
    realized_r: Mapped[float] = mapped_column(Float, nullable=True)
    target_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stop_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bars_to_target: Mapped[int] = mapped_column(Integer, nullable=True)
    labeled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )

    recommendation: Mapped["RecommendationRecord"] = relationship(back_populates="outcome")
