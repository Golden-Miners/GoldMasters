"""Settings startup validation tests (01-10 Task 1: explicit keys, fail-loud)."""

from __future__ import annotations

import pytest
from goldmasters_api.settings import Settings
from pydantic import SecretStr, ValidationError
from pydantic_settings.sources import YamlConfigSettingsSource

DB = "postgresql+psycopg://goldmasters:secret@127.0.0.1:5432/goldmasters"


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every GOLDMASTERS_ variable so each test controls its env fully."""
    import os

    for key in [k for k in os.environ if k.startswith("GOLDMASTERS_")]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GOLDMASTERS_DATABASE_URL", DB)


def test_missing_required_key_names_it(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GOLDMASTERS_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings()  # type: ignore[call-arg]


def test_invalid_value_names_the_key(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GOLDMASTERS_BIND_PORT", "not-a-port")
    with pytest.raises(ValidationError, match="bind_port"):
        Settings()  # type: ignore[call-arg]


def test_unknown_prefixed_variable_rejected(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GOLDMASTERS_TYPO_HOTS", "127.0.0.1")
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


def test_declared_key_set(clean_env: pytest.FixtureRequest) -> None:
    assert set(Settings.model_fields) == {
        "bind_host",
        "bind_port",
        "database_url",
        "trace_file_path",
        "log_level",
        "config_version",
        "provider_api_key",
    }


def test_secret_field_hidden(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GOLDMASTERS_PROVIDER_API_KEY", "super-secret-value")
    settings = Settings()  # type: ignore[call-arg]
    assert isinstance(settings.provider_api_key, SecretStr)
    assert "super-secret-value" not in repr(settings)
    assert "super-secret-value" not in str(settings.model_dump())


def test_yaml_source_is_live_and_last() -> None:
    from typing import cast

    from pydantic_settings import PydanticBaseSettingsSource

    sentinel = cast(PydanticBaseSettingsSource, object())
    sources = Settings.settings_customise_sources(Settings, sentinel, sentinel, sentinel, sentinel)
    assert isinstance(sources[-1], YamlConfigSettingsSource)


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> Settings:
    for key, value in overrides.items():
        monkeypatch.setenv(f"GOLDMASTERS_{key.upper()}", value)
    return Settings()  # type: ignore[call-arg]


def test_hash_deterministic(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    from goldmasters_api.settings import hash_effective_config

    settings = _settings(monkeypatch)
    assert hash_effective_config(settings) == hash_effective_config(settings)


def test_hash_order_invariant(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib
    import json

    from goldmasters_api.settings import HASH_ALGORITHM_VERSION, hash_effective_config

    settings = _settings(monkeypatch)
    digest = hash_effective_config(settings)
    payload = settings.model_dump()
    reordered = dict(reversed(list(payload.items())))
    canonical = json.dumps(
        {
            **{k: v for k, v in reordered.items() if k != "provider_api_key"},
            "_hash_algorithm_version": HASH_ALGORITHM_VERSION,
        },
        sort_keys=True,
        default=str,
    )
    assert hashlib.sha256(canonical.encode()).hexdigest() == digest


def test_hash_ignores_secrets(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    from goldmasters_api.settings import hash_effective_config

    before = hash_effective_config(_settings(monkeypatch))
    after = hash_effective_config(_settings(monkeypatch, provider_api_key="changed"))
    assert before == after


def test_hash_moves_with_non_secret(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    from goldmasters_api.settings import hash_effective_config

    before = hash_effective_config(_settings(monkeypatch))
    after = hash_effective_config(_settings(monkeypatch, bind_port="8001"))
    assert before != after


def test_hash_algorithm_version_exposed(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib
    import json

    from goldmasters_api.settings import (
        HASH_ALGORITHM_VERSION,
        hash_effective_config,
    )
    from goldmasters_api.settings import (
        Settings as SettingsModel,
    )

    assert HASH_ALGORITHM_VERSION == "1"
    assert SettingsModel.model_fields["config_version"].default == "1.0"
    settings = _settings(monkeypatch)
    payload = {k: v for k, v in settings.model_dump().items() if k != "provider_api_key"}
    digest_v2 = hashlib.sha256(
        json.dumps(
            {**payload, "_hash_algorithm_version": "2"}, sort_keys=True, default=str
        ).encode()
    ).hexdigest()
    assert digest_v2 != hash_effective_config(settings)
