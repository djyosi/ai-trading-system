from sqlalchemy import inspect, text

from app.db.base import Base
from app.models import OutcomeRecord, RecommendationRecord  # noqa: F401

_RECOMMENDATION_METADATA_COLUMNS = {
    "strategy_segment": "VARCHAR(160)",
    "research_tags": "JSON",
    "research_evidence": "JSON",
}


def ensure_schema(engine):
    """Create MVP tables and add lightweight SQLite-safe columns added during development."""
    Base.metadata.create_all(bind=engine)
    _ensure_recommendation_metadata_columns(engine)


def _ensure_recommendation_metadata_columns(engine):
    inspector = inspect(engine)
    if "recommendations" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("recommendations")}
    missing = {
        column_name: column_type
        for column_name, column_type in _RECOMMENDATION_METADATA_COLUMNS.items()
        if column_name not in existing_columns
    }
    if not missing:
        return

    with engine.begin() as connection:
        for column_name, column_type in missing.items():
            connection.execute(text(f"ALTER TABLE recommendations ADD COLUMN {column_name} {column_type}"))
