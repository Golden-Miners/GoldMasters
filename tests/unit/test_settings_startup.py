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
    monkeypatch.setenv("GOLDMASTERS_MT5_SERVER_TIMEZONE", "UTC")


def test_missing_required_key_names_it(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    from goldmasters_api.settings import Settings as SettingsModel
    from pydantic_settings import SettingsConfigDict

    class NoDotenvSettings(SettingsModel):
        model_config = SettingsConfigDict(
            env_prefix="GOLDMASTERS_",
            env_file=None,
            extra="forbid",
            frozen=True,
            yaml_file="config/goldmasters.yaml",
        )

    monkeypatch.delenv("GOLDMASTERS_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        NoDotenvSettings()  # type: ignore[call-arg]


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
        # Phase 2 D-59 market-data keys (02-01 tracer).
        "provider_id",
        "instrument_id",
        "mt5_symbol",
        "timeframe",
        "mt5_server_timezone",
        "mt5_probe_timeout_seconds",
        "mt5_retry_attempts",
        "mt5_retry_delay_ms",
        "mt5_bars_count",
        "bar_stale_closed_bars",
        "bar_stale_grace_seconds",
        "quote_stale_seconds_overlap",
        "quote_stale_seconds_major",
        "quote_stale_seconds_asia",
        "quote_stale_seconds_offhours",
        "weekend_close_utc",
        "daily_break_utc",
        # Phase 2 D-57/D-59 session windows (02-02).
        "session_overlap_utc",
        "session_major_utc",
        "session_asia_utc",
    }


def test_no_mt5_secret_key_declared(clean_env: pytest.FixtureRequest) -> None:
    """D-47: the server timezone is the only GOLDMASTERS_MT5_* key, never secret."""
    from goldmasters_api.settings import _is_secret_field

    settings = Settings()  # type: ignore[call-arg]
    mt5_keys = [n for n in Settings.model_fields if n.startswith("mt5_")]
    assert mt5_keys, "expected MT5 settings keys to exist"
    for name in mt5_keys:
        assert not _is_secret_field(settings, name), f"secret MT5 key declared: {name}"
    assert "mt5_server_timezone" in mt5_keys


def test_server_timezone_required_names_key(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail-closed startup on a missing/invalid server timezone (D-36)."""
    monkeypatch.delenv("GOLDMASTERS_MT5_SERVER_TIMEZONE", raising=False)
    with pytest.raises(ValidationError, match="mt5_server_timezone"):
        Settings()  # type: ignore[call-arg]
    monkeypatch.setenv("GOLDMASTERS_MT5_SERVER_TIMEZONE", "Not/AZone")
    with pytest.raises(ValidationError, match="mt5_server_timezone"):
        Settings()  # type: ignore[call-arg]


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


def test_malformed_window_specs_fail_closed(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-36: a malformed session/weekend/break window names its key, never defaults."""
    from pydantic import ValidationError as PydanticValidationError

    for key, bad in (
        ("GOLDMASTERS_SESSION_OVERLAP_UTC", "13:00"),
        ("GOLDMASTERS_WEEKEND_CLOSE_UTC", "Friday-Sunday"),
        ("GOLDMASTERS_DAILY_BREAK_UTC", "21:00-21:00,22:00-23:00"),
    ):
        monkeypatch.setenv(key, bad)
        with pytest.raises(PydanticValidationError, match=key.split("GOLDMASTERS_")[1].lower()):
            Settings()  # type: ignore[call-arg]
        monkeypatch.delenv(key)


def test_hash_moves_with_every_d59_key(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-15/D-27/D-59: each threshold/session/selection key joins the hashed config.

    One mutation per key; a silent type-based exclusion would leave the digest
    unchanged and fail this test.
    """
    from goldmasters_api.settings import hash_effective_config

    mutations = {
        "provider_id": "mt5_backup",
        "instrument_id": "eurusd",
        "mt5_symbol": "XAUUSDm",
        "timeframe": "H4",
        "mt5_server_timezone": "Europe/Athens",
        "mt5_probe_timeout_seconds": "3.0",
        "mt5_retry_attempts": "2",
        "mt5_retry_delay_ms": "600",
        "mt5_bars_count": "11",
        "bar_stale_closed_bars": "3",
        "bar_stale_grace_seconds": "301",
        "quote_stale_seconds_overlap": "31",
        "quote_stale_seconds_major": "61",
        "quote_stale_seconds_asia": "181",
        "quote_stale_seconds_offhours": "301",
        "session_overlap_utc": "13:00-16:00",
        "session_major_utc": "08:00-13:00,16:30-20:00",
        "session_asia_utc": "00:00-07:00",
        "weekend_close_utc": "Fri 21:00-Sun 21:00",
        "daily_break_utc": "21:00-22:30",
    }
    baseline = hash_effective_config(_settings(monkeypatch))
    assert set(mutations) <= set(Settings.model_fields)
    for key, value in mutations.items():
        env_name = f"GOLDMASTERS_{key.upper()}"
        import os

        previous = os.environ.get(env_name)
        monkeypatch.setenv(env_name, value)
        digest = hash_effective_config(Settings())  # type: ignore[call-arg]
        assert digest != baseline, f"hash is blind to D-59 key {key}"
        if previous is None:
            monkeypatch.delenv(env_name)
        else:
            monkeypatch.setenv(env_name, previous)
