"""Chain-proof health surface (D-31; Schema.md §1 line 18).

``GET /health`` returns five fields proving the settings → app → health
chain: ``status``, ``version``, ``contract_schema_version``, ``config_hash``
and a ``database`` object whose ``reachable`` key is a boolean — plus a
``provider`` object from the bounded MT5 probe (Phase 2): ``provider_id``,
``status``, ``market_open``, ``terminal_build``, ``last_bar_close_time``,
``last_quote_time``, ``checked_at``. Both probes are bounded, never raise,
and never echo connection strings, terminal internals, or raw payloads.
"""

from __future__ import annotations

import goldmasters_contracts
from fastapi import APIRouter, Request
from sqlalchemy import create_engine, text

import goldmasters_api
from services.mt5_adapter.adapter import probe_mt5

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
    except Exception:  # noqa: BLE001 — probe contract: every failure maps to False
        # Any failure — unreachable host, bad URL, driver error — is a
        # value, not an exception: reachable False, URL never echoed.
        return False


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    """Five-field health surface plus the bounded provider object."""
    settings = request.app.state.settings
    reachable = probe_database(settings.database_url)
    provider = probe_mt5(
        request.app.state.mt5_gateway,
        server_timezone=settings.mt5_server_timezone,
        timeout_seconds=settings.mt5_probe_timeout_seconds,
        bars_count=settings.mt5_bars_count,
    )
    return {
        "status": "ok",
        "version": goldmasters_api.__version__,
        "contract_schema_version": goldmasters_contracts.CONTRACT_VERSION,
        "config_hash": request.app.state.config_hash,
        "database": {"reachable": reachable},
        "provider": provider,
    }
