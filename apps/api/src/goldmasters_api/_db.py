"""Database engine helper for read-only routers."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

__all__ = ["engine_from_url"]


def engine_from_url(url: str) -> Engine:
    """Create a short-timeout engine for read-only queries."""
    return create_engine(url, connect_args={"connect_timeout": 2})
