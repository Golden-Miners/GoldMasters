"""Typed settings resolved once at startup (D-15/D-27/D-36).

Every key the skeleton and its later phases use is declared explicitly; an
unknown ``GOLDMASTERS_``-prefixed variable is rejected (``extra="forbid"``),
and a missing or invalid key stops startup naming the key. Secrets arrive
only through ``GOLDMASTERS_``-prefixed variables and are typed ``SecretStr``.

The versioned ``config/goldmasters.yaml`` document is wired as the
lowest-priority source (after init, environment, ``.env`` and secrets), so an
operator override always wins. :func:`hash_effective_config` covers the
non-secret fields only — derived from field *types*, so a new secret field is
excluded automatically — and carries :data:`HASH_ALGORITHM_VERSION` so a
future canonicalisation change is detectable.
"""

from __future__ import annotations

import hashlib
import json
import os
import typing
from typing import Any

from pydantic import SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

__all__ = ["HASH_ALGORITHM_VERSION", "Settings", "hash_effective_config"]

#: Version of the hash canonicalisation. Bumping this changes every digest by
#: construction, so a canonicalisation change is detectable, never silent.
HASH_ALGORITHM_VERSION = "1"


class Settings(BaseSettings):
    """Full declared key set. Plan 09 consumes `trace_file_path`/`log_level`."""

    model_config = SettingsConfigDict(
        env_prefix="GOLDMASTERS_",
        env_file=".env",
        extra="forbid",
        frozen=True,
        yaml_file="config/goldmasters.yaml",
    )

    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    database_url: str
    trace_file_path: str = "logs/traces.jsonl"
    log_level: str = "INFO"
    config_version: str = "1.0"
    provider_api_key: SecretStr | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_undeclared_prefixed_variables(cls, data: Any) -> Any:
        """Reject a `GOLDMASTERS_`-prefixed variable no field declares (D-36).

        pydantic-settings ignores environment names with no matching field,
        so a typo would silently default; this guard names the offender
        instead. Runs on every construction path, including startup.
        """
        declared = {f"GOLDMASTERS_{name.upper()}" for name in cls.model_fields}
        unknown = sorted(
            key for key in os.environ if key.startswith("GOLDMASTERS_") and key not in declared
        )
        if unknown:
            raise ValueError(f"undeclared GOLDMASTERS_ variable(s): {', '.join(unknown)}")
        return data

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Default sources plus the versioned YAML document, last (D-15)."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSettingsSource(settings_cls),
        )


def _is_secret_field(settings: Settings, name: str) -> bool:
    """True when the field's type involves `SecretStr` (excluded by type)."""
    annotation = type(settings).model_fields[name].annotation
    return annotation is SecretStr or SecretStr in typing.get_args(annotation)


def hash_effective_config(settings: Settings) -> str:
    """Hash the canonical JSON of the non-secret settings (sha256 hex).

    Sorted keys make the digest order-invariant; the embedded algorithm
    version makes a canonicalisation change detectable.
    """
    payload = {
        key: value
        for key, value in settings.model_dump().items()
        if not _is_secret_field(settings, key)
    }
    payload["_hash_algorithm_version"] = HASH_ALGORITHM_VERSION
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
