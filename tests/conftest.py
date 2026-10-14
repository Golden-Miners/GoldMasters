"""Throwaway per-run database fixtures (D-35).

Every test database is created uniquely per run and dropped at teardown —
tests never mutate the persistent working instance. The target derives from
the API's validated `Settings`/`GOLDMASTERS_DATABASE_URL`, so it can never
diverge from the working configuration's host and credentials. Missing
prerequisites fail loudly instead of skipping: criterion 5 requires the test
to have actually run.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from collections.abc import Generator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

REPO = Path(__file__).resolve().parents[1]


def _working_url() -> str:
    """Resolve the working URL through the API's Settings (D-27)."""
    from goldmasters_api.settings import Settings

    try:
        return Settings().database_url  # type: ignore[call-arg]
    except Exception as exc:
        raise RuntimeError(
            "GOLDMASTERS_DATABASE_URL is not resolvable through Settings; "
            "the database-backed tests cannot run without it."
        ) from exc


def _replace_database(url: str, database: str) -> str:
    parsed = make_url(url)
    password = f":{quote_plus(parsed.password)}" if parsed.password else ""
    host = f"@{parsed.host}" if parsed.host else ""
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.drivername}://{parsed.username}{password}{host}{port}/{database}"


def _ensure_cluster_running() -> None:
    """Start the repo-local cluster idempotently (bounded)."""
    script = REPO / "scripts" / "postgres" / "start.ps1"
    if not script.is_file():
        raise RuntimeError(f"cluster start script missing: {script}")
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(script)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=REPO,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cluster failed to start:\n{result.stdout}\n{result.stderr}")


@pytest.fixture(scope="session")
def throwaway_database() -> Generator[str]:
    """Create a uniquely named database; drop it (with connections) at teardown."""
    _ensure_cluster_running()
    working = _working_url()
    suffix = uuid.uuid4().hex[:8]
    parsed = make_url(working)
    stem = (parsed.database or "goldmasters").split("_test_")[0]
    test_database = f"{stem}_test_{suffix}"
    maintenance = _replace_database(working, "postgres")
    engine = create_engine(maintenance, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{test_database}"'))
    engine.dispose()
    try:
        yield _replace_database(working, test_database)
    finally:
        admin = create_engine(maintenance, isolation_level="AUTOCOMMIT")
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": test_database},
            )
            connection.execute(text(f'DROP DATABASE "{test_database}"'))
        admin.dispose()


@pytest.fixture(scope="session")
def database_url(throwaway_database: str) -> str:
    """Per-run database URL."""
    return throwaway_database


@pytest.fixture(scope="session")
def migrated_database(
    throwaway_database: str,
) -> Generator[str]:
    """Throwaway database with `alembic upgrade head` applied."""
    from alembic.command import upgrade
    from alembic.config import Config

    previous = os.environ.get("GOLDMASTERS_DATABASE_URL")
    os.environ["GOLDMASTERS_DATABASE_URL"] = throwaway_database
    try:
        config = Config(str(REPO / "apps" / "api" / "alembic.ini"))
        config.set_main_option("script_location", str(REPO / "apps" / "api" / "migrations"))
        upgrade(config, "head")
        yield throwaway_database
    finally:
        if previous is None:
            os.environ.pop("GOLDMASTERS_DATABASE_URL", None)
        else:
            os.environ["GOLDMASTERS_DATABASE_URL"] = previous
