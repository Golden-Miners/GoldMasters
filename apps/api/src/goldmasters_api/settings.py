"""Typed settings resolved once at startup (D-15/D-27/D-31).

Every value arrives through a ``GOLDMASTERS_``-prefixed environment variable;
``extra="forbid"`` rejects anything undeclared. :func:`hash_effective_config`
covers the non-secret fields only, so the config hash in ``/health`` proves
which configuration is running without leaking a secret. Plan 10 extends the
field set and hardens secret exclusion by field type.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "hash_effective_config"]


class Settings(BaseSettings):
    """Minimal Phase 1 settings. Plan 10 extends this to the full key set."""

    model_config = SettingsConfigDict(
        env_prefix="GOLDMASTERS_", env_file=".env", extra="forbid", frozen=True
    )

    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    database_url: str = "postgresql+psycopg://127.0.0.1:5432/goldmasters"
    config_version: str = "1.0"
    secret: SecretStr | None = None


#: Fields excluded from the effective-config hash (secret-bearing).
_SECRET_FIELDS = frozenset({"secret"})


def hash_effective_config(settings: Settings) -> str:
    """Hash the canonical JSON of the non-secret settings (sha256 hex)."""
    payload = {
        key: value
        for key, value in settings.model_dump().items()
        if key not in _SECRET_FIELDS
    }
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
