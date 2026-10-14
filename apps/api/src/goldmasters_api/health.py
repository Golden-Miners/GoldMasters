"""Chain-proof health surface (D-31; Schema.md §1 line 18).

``GET /health`` returns five fields proving the settings → app → health
chain: ``status``, ``version``, ``contract_schema_version``, ``config_hash``
and a ``database`` object whose ``reachable`` key is a boolean. The probe is
bounded by a short timeout, reports ``False`` instead of raising, and never
echoes the connection string or any fragment of it.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

import goldmasters_api
import goldmasters_contracts

__all__ = ["probe_database", "router"]

router = APIRouter()

#: Bound on the database probe so a black-holed address cannot hang /health.
_PROBE_TIMEOUT_SECONDS = 2


def probe_database(database_url: str) -> bool:
    """Return reachability. Never raises; never leaks the URL."""
    try:
        engine = create_engine(
            database_url, connect_args={"connect_timeout": _PROBE_TIMEOUT_SECONDS}
        )
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except SQLAlchemyError:
        return False
    except Exception:
        return False


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    """Five-field health surface read from app state, never hard-coded."""
    settings = request.app.state.settings
    reachable = probe_database(settings.database_url)
    return {
        "status": "ok",
        "version": goldmasters_api.__version__,
        "contract_schema_version": goldmasters_contracts.CONTRACT_VERSION,
        "config_hash": request.app.state.config_hash,
        "database": {"reachable": reachable},
    }
