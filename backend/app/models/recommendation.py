from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.outcome import OutcomeRecord


class RecommendationRecord(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    setup_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy: Mapped[str] = mapped_column(String(96), index=True, nullable=False)
    entry_trigger: Mapped[str] = mapped_column(String(160), nullable=False)
    entry_zone: Mapped[list] = mapped_column(JSON, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=True)
    targets: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_reward: Mapped[float] = mapped_column(Float, nullable=True)
    invalid_if: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reject_reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )

    outcome: Mapped["OutcomeRecord"] = relationship(back_populates="recommendation", uselist=False)
