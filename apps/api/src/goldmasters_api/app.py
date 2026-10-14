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

from goldmasters_api.health import router as health_router
from goldmasters_api.logging import configure_logging
from goldmasters_api.middleware import CorrelationIdMiddleware
from goldmasters_api.settings import Settings, hash_effective_config
from goldmasters_api.tracing import configure_tracing, shutdown_tracing

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
    """Resolve settings once; fail startup on a non-loopback bind."""
    settings = Settings()  # type: ignore[call-arg]  # required keys arrive via env
    assert_loopback(settings.bind_host)
    configure_logging(settings.log_level)
    configure_tracing(settings.trace_file_path)
    app.state.settings = settings
    app.state.config_hash = hash_effective_config(settings)
    yield
    shutdown_tracing()


def create_app() -> FastAPI:
    """Build the API application."""
    application = FastAPI(title="GoldMasters Research API", lifespan=lifespan)
    application.add_middleware(CorrelationIdMiddleware)
    application.include_router(health_router)
    return application


app = create_app()
