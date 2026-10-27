"""FastAPI application factory with loopback guard (D-34) and observability.

``lifespan`` resolves :class:`Settings` once, refuses a non-loopback bind
host, configures redacted JSON logging plus on-disk tracing, and stores the
settings plus the effective-config hash on ``app.state``.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from goldmasters_api.agent_runs import router as agent_runs_router
from goldmasters_api.backtests import router as backtests_router

# Read-only console API routers (Phase 7)
from goldmasters_api.decisions import router as decisions_router
from goldmasters_api.health import router as health_router
from goldmasters_api.journal import router as journal_router
from goldmasters_api.app_logging import configure_logging
from goldmasters_api.market import router as market_router
from goldmasters_api.middleware import CorrelationIdMiddleware
from goldmasters_api.model_health import router as model_health_router
from goldmasters_api.news_sentiment import router as news_sentiment_router
from goldmasters_api.providers import router as providers_router
from goldmasters_api.settings import Settings, hash_effective_config
from goldmasters_api.settings_router import router as settings_router
from goldmasters_api.strategies import router as strategies_router
from goldmasters_api.tracing import configure_tracing, shutdown_tracing
from services.mt5_adapter.adapter import Mt5Adapter
from services.mt5_adapter.symbol_resolver import SymbolResolver
from services.mt5_adapter.terminal import (
    BROKER_SYMBOL_ALIASES,
    Mt5Gateway,
    TerminalManager,
)

__all__ = ["app", "assert_loopback", "create_app"]


def assert_loopback(host: str) -> None:
    """Accept a loopback bind host; raise naming any other host (D-34)."""
    candidates: list[str] = [host]
    if host == "localhost":
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise ValueError(f"bind_host {host!r} does not resolve to loopback") from exc
        candidates = sorted({str(info[4][0]) for info in infos})
    for candidate in candidates:
        try:
            parsed = ipaddress.ip_address(candidate)
        except ValueError as exc:
            raise ValueError(f"bind_host {host!r} is not a loopback address") from exc
        if not parsed.is_loopback:
            raise ValueError(f"bind_host {host!r} is not a loopback address")
    if host == "localhost" and not candidates:
        raise ValueError(f"bind_host {host!r} does not resolve to loopback")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Resolve settings once; fail startup on a non-loopback bind.

    Starts the MT5 TerminalManager (persistent IPC connection) and
    SymbolResolver (broker-aware symbol resolution) during application
    startup so individual reads never call initialize()/shutdown().
    """
    settings = Settings()  # type: ignore[call-arg]  # required keys arrive via env
    assert_loopback(settings.bind_host)
    configure_logging(settings.log_level)
    configure_tracing(settings.trace_file_path)
    app.state.settings = settings
    app.state.config_hash = hash_effective_config(settings)

    # Start MT5 terminal manager (persistent connection)
    gateway = Mt5Gateway()
    terminal_manager = TerminalManager(
        gateway,
        terminal_path=settings.mt5_terminal_path,
        startup_timeout_seconds=settings.mt5_startup_timeout_seconds,
    )
    terminal_manager.start()
    app.state.mt5_terminal_manager = terminal_manager

    # Start symbol resolver (broker-aware symbol resolution)
    symbol_resolver = SymbolResolver(gateway, BROKER_SYMBOL_ALIASES)
    app.state.mt5_symbol_resolver = symbol_resolver

    yield

    # Clean shutdown
    terminal_manager.stop()
    shutdown_tracing()


def create_app(
    terminal_manager: TerminalManager | None = None,
    symbol_resolver: SymbolResolver | None = None,
) -> FastAPI:
    """Build the API application.

    Args:
        terminal_manager: MT5 terminal manager; defaults to a live
            TerminalManager backed by Mt5Gateway. Tests inject a double.
        symbol_resolver: MT5 symbol resolver; defaults to a live
            SymbolResolver backed by Mt5Gateway. Tests inject a double.
    """
    application = FastAPI(title="GoldMasters Research API", lifespan=lifespan)
    application.add_middleware(CorrelationIdMiddleware)

    # Core health + market data (Phase 2)
    application.include_router(health_router)
    application.include_router(market_router)

    # Phase 7: read-only console API routers (11 surfaces)
    application.include_router(decisions_router)
    application.include_router(news_sentiment_router)
    application.include_router(strategies_router)
    application.include_router(backtests_router)
    application.include_router(journal_router)
    application.include_router(agent_runs_router)
    application.include_router(providers_router)
    application.include_router(model_health_router)
    application.include_router(settings_router)

    application.state.mt5_terminal_manager = terminal_manager or TerminalManager(
        Mt5Gateway()
    )
    application.state.mt5_symbol_resolver = symbol_resolver or SymbolResolver(
        application.state.mt5_terminal_manager._gateway
    )
    return application


app = create_app()


app = create_app()