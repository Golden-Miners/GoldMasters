"""Settings startup validation tests (01-10 Task 1: explicit keys, fail-loud)."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError
from pydantic_settings.sources import YamlConfigSettingsSource

from goldmasters_api.settings import Settings

DB = "postgresql+psycopg://goldmasters:secret@127.0.0.1:5432/goldmasters"


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every GOLDMASTERS_ variable so each test controls its env fully."""
    import os

    for key in [k for k in os.environ if k.startswith("GOLDMASTERS_")]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GOLDMASTERS_DATABASE_URL", DB)


def test_missing_required_key_names_it(clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOLDMASTERS_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings()  # type: ignore[call-arg]


def test_invalid_value_names_the_key(clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOLDMASTERS_BIND_PORT", "not-a-port")
    with pytest.raises(ValidationError, match="bind_port"):
        Settings()  # type: ignore[call-arg]


def test_unknown_prefixed_variable_rejected(clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_secret_field_hidden(clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOLDMASTERS_PROVIDER_API_KEY", "super-secret-value")
    settings = Settings()  # type: ignore[call-arg]
    assert isinstance(settings.provider_api_key, SecretStr)
    assert "super-secret-value" not in repr(settings)
    assert "super-secret-value" not in str(settings.model_dump())


def test_yaml_source_is_live_and_last() -> None:
    sources = Settings.settings_customise_sources(
        Settings, object(), object(), object(), object()  # type: ignore[arg-type]
    )
    assert isinstance(sources[-1], YamlConfigSettingsSource)
