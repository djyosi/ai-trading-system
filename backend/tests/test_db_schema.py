from sqlalchemy import create_engine, inspect, text

from app.db.schema import ensure_schema


def test_ensure_schema_adds_recommendation_metadata_columns_to_existing_sqlite_table():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE recommendations (
                    id INTEGER PRIMARY KEY,
                    ticker VARCHAR(16) NOT NULL,
                    timeframe VARCHAR(32) NOT NULL,
                    direction VARCHAR(32) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    setup_score INTEGER NOT NULL,
                    confidence VARCHAR(32) NOT NULL,
                    strategy VARCHAR(96) NOT NULL,
                    entry_trigger VARCHAR(160) NOT NULL,
                    entry_zone JSON,
                    stop_loss FLOAT,
                    targets JSON NOT NULL,
                    risk_reward FLOAT,
                    invalid_if JSON NOT NULL,
                    reject_reasons JSON NOT NULL,
                    warnings JSON NOT NULL,
                    reason TEXT NOT NULL,
                    input_snapshot JSON NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )

    ensure_schema(engine)

    column_names = {column["name"] for column in inspect(engine).get_columns("recommendations")}
    assert "strategy_segment" in column_names
    assert "research_tags" in column_names
    assert "research_evidence" in column_names


def test_ensure_schema_is_idempotent_for_fresh_schema():
    engine = create_engine("sqlite:///:memory:")

    ensure_schema(engine)
    ensure_schema(engine)

    column_names = {column["name"] for column in inspect(engine).get_columns("recommendations")}
    assert "strategy_segment" in column_names
    assert "research_tags" in column_names
    assert "research_evidence" in column_names
