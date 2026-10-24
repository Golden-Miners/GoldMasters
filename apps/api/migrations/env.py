"""Alembic environment: URL always from validated Settings (D-07/D-27).

No hard-coded literal, no second credential store — the same
`GOLDMASTERS_DATABASE_URL` the API uses, so `scripts/stack` and the test
suite migrate identically-shaped databases.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

# Allow `from goldmasters_api.settings import Settings` regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# Allow `from services.mt5_adapter.validation import ...` regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from goldmasters_api.settings import Settings  # noqa: E402

config = context.config


def _database_url() -> str:
    return Settings().database_url  # type: ignore[call-arg]  # resolved from env


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    engine = create_engine(_database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
