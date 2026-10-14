"""Migration apply → rollback → re-apply against a throwaway database (01-06 Task 2)."""

from __future__ import annotations

from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from tests.conftest import REPO


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
    assert "contract_document" in tables
    assert "ix_contract_document_run_id" in indexes
    assert "ix_contract_document_instrument_id" in indexes

    downgrade(_config(), "base")
    tables, indexes = _tables_and_indexes(migrated_database)
    assert "contract_document" not in tables
    assert not {name for name in indexes if "contract_document" in name}

    upgrade(_config(), "head")
    tables, _ = _tables_and_indexes(migrated_database)
    assert "contract_document" in tables
