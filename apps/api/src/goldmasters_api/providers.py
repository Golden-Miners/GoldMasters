"""Read-only providers router: bounded MT5 provider probe."""

from __future__ import annotations

from fastapi import APIRouter, Request

from services.mt5_adapter.adapter import probe_mt5

__all__ = ["router"]

router = APIRouter(prefix="/v1/providers")


@router.get("", response_model=None)
def read_providers(request: Request) -> dict[str, object]:
    """Bounded provider probe. Never raises; returns disconnected on failure."""
    settings = request.app.state.settings
    return probe_mt5(
        request.app.state.mt5_terminal_manager,
        request.app.state.mt5_symbol_resolver,
        server_timezone=settings.mt5_server_timezone,
        bars_count=settings.mt5_bars_count,
        weekend_spec=settings.weekend_close_utc,
    )
