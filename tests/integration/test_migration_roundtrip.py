"""Migration apply → rollback → re-apply against a throwaway database (01-06 Task 2).

Extended in 06-01 for 0002/0003: the same cycle asserts the journal, outcome,
backtest, and manifest tables plus their indexes at each stage.
"""

from __future__ import annotations

from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from tests.conftest import REPO

_TABLES = frozenset(
    {
        "contract_document",
        "journal_entry",
        "outcome_observation",
        "backtest_run",
        "dataset_manifest",
    }
)

_INDEXES = frozenset(
    {
        "ix_contract_document_run_id",
        "ix_contract_document_instrument_id",
        "ix_journal_entry_decision_id",
        "ix_journal_entry_run_id",
        "ix_outcome_observation_decision_id",
        "ix_backtest_run_strategy_id",
    }
)


def _config() -> Config:
    config = Config(str(REPO / "apps" / "api" / "alembic.ini"))
    config.set_main_option("script_location", str(REPO / "apps" / "api" / "migrations"))
    return config


def _tables_and_indexes(url: str) -> tuple[set[str], set[str]]:
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        indexes: set[str] = set()
        for table in tables:
            indexes.update(index["name"] for index in inspector.get_indexes(table) if index["name"])
        return tables, indexes
    finally:
        engine.dispose()


def test_migration_roundtrip(migrated_database: str) -> None:
    tables, indexes = _tables_and_indexes(migrated_database)
    assert _TABLES <= tables
    assert _INDEXES <= indexes

    downgrade(_config(), "base")
    tables, indexes = _tables_and_indexes(migrated_database)
    assert not (_TABLES & tables)
    assert not {name for name in indexes if "contract_document" in name}
    assert not {name for name in indexes if "journal_entry" in name}
    assert not {name for name in indexes if "outcome_observation" in name}
    assert not {name for name in indexes if "backtest_run" in name}

    upgrade(_config(), "head")
    tables, indexes = _tables_and_indexes(migrated_database)
    assert _TABLES <= tables
    assert _INDEXES <= indexes
