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
        # Phase 3 D-3.1/D-3.2 policy keys (03-01 tracer).
        "tick_rounding_mode",
        "max_risk_percent_per_idea",
        "min_risk_reward_ratio",
        # Phase 3.1 strategy-agent scaffold rows (03.1-01 framework).
        "strategy_agent_01_enabled",
        "strategy_agent_01_instruments",
        "strategy_agent_01_timeframes",
        "strategy_agent_01_regimes",
        "strategy_agent_01_min_bars",
        "strategy_agent_01_fast_period",
        "strategy_agent_01_slow_period",
        "strategy_agent_01_htf_timeframe",
        "strategy_agent_01_adx_min",
        "strategy_agent_01_confirm_bars",
        "strategy_agent_02_enabled",
        "strategy_agent_02_instruments",
        "strategy_agent_02_timeframes",
        "strategy_agent_02_regimes",
        "strategy_agent_02_min_bars",
        "strategy_agent_02_lookbacks",
        "strategy_agent_02_entry_threshold",
        "strategy_agent_02_vol_lookback",
        "strategy_agent_02_max_hold_bars",
        "strategy_agent_02_expiry_bars",
        "strategy_agent_03_enabled",
        "strategy_agent_03_instruments",
        "strategy_agent_03_timeframes",
        "strategy_agent_03_regimes",
        "strategy_agent_03_min_bars",
        "strategy_agent_03_channel_bars",
        "strategy_agent_03_buffer_ticks",
        "strategy_agent_03_confirm_bars",
        "strategy_agent_03_exit_bars",
        "strategy_agent_04_enabled",
        "strategy_agent_04_instruments",
        "strategy_agent_04_timeframes",
        "strategy_agent_04_regimes",
        "strategy_agent_04_min_bars",
        "strategy_agent_04_vol_lookback",
        "strategy_agent_04_compression_pctile",
        "strategy_agent_04_confirm_bars",
        "strategy_agent_05_enabled",
        "strategy_agent_05_instruments",
        "strategy_agent_05_timeframes",
        "strategy_agent_05_regimes",
        "strategy_agent_05_min_bars",
        "strategy_agent_05_trend_period",
        "strategy_agent_05_pullback_ma",
        "strategy_agent_05_confirm_bars",
        "strategy_agent_05_expiry_bars",
        "strategy_agent_06_enabled",
        "strategy_agent_06_instruments",
        "strategy_agent_06_timeframes",
        "strategy_agent_06_regimes",
        "strategy_agent_06_min_bars",
        "strategy_agent_06_session_name",
        "strategy_agent_06_session_tz",
        "strategy_agent_06_range_minutes",
        "strategy_agent_06_buffer_ticks",
        "strategy_agent_06_expiry_minutes",
        "strategy_agent_06_max_spread_ticks",
        "strategy_agent_07_enabled",
        "strategy_agent_07_instruments",
        "strategy_agent_07_timeframes",
        "strategy_agent_07_regimes",
        "strategy_agent_07_min_bars",
        "strategy_agent_07_basis_period",
        "strategy_agent_07_band_width",
        "strategy_agent_07_z_min",
        "strategy_agent_07_rsi_period",
        "strategy_agent_07_rsi_extreme",
        "strategy_agent_07_confirm_bars",
        "strategy_agent_08_enabled",
        "strategy_agent_08_instruments",
        "strategy_agent_08_timeframes",
        "strategy_agent_08_regimes",
        "strategy_agent_08_min_bars",
        "strategy_agent_08_session_name",
        "strategy_agent_08_session_tz",
        "strategy_agent_08_band_sigmas",
        "strategy_agent_08_min_volume_bars",
        "strategy_agent_09_enabled",
        "strategy_agent_09_instruments",
        "strategy_agent_09_timeframes",
        "strategy_agent_09_regimes",
        "strategy_agent_09_min_bars",
        "strategy_agent_09_swing_bars",
        "strategy_agent_09_equal_tol_ticks",
        "strategy_agent_09_sweep_tol_ticks",
        "strategy_agent_09_disp_body_min_atr",
        "strategy_agent_09_expiry_bars",
        "strategy_agent_10_enabled",
        "strategy_agent_10_instruments",
        "strategy_agent_10_timeframes",
        "strategy_agent_10_regimes",
        "strategy_agent_10_min_bars",
        "strategy_agent_10_max_data_age_hours",
        "strategy_agent_10_min_history_points",
        "graph_node_timeout_seconds",
        "graph_node_max_retries",
        "graph_max_concurrency",
        # Phase 6 cost model (D-6.1).
        "cost_spread",
        "cost_commission",
        "cost_slippage",
        "cost_swap",
        "cost_profiles",
        # Phase 4 Wave 2 model runtime (04-03 tracer).
        "ollama_host",
        "ollama_model",
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
        "max_risk_percent_per_idea": "1.0",
        "min_risk_reward_ratio": "2.0",
    }
    for agent in ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10"):
        mutations[f"strategy_agent_{agent}_enabled"] = "true"
        mutations[f"strategy_agent_{agent}_instruments"] = "xauusd"
        mutations[f"strategy_agent_{agent}_timeframes"] = "H1"
        mutations[f"strategy_agent_{agent}_regimes"] = "uptrend"
        mutations[f"strategy_agent_{agent}_min_bars"] = "20"
    # Phase 3.2 agent 1-5 rule numerics join the hashed config (operator placeholders).
    mutations.update(
        {
            "strategy_agent_01_fast_period": "3",
            "strategy_agent_01_slow_period": "5",
            "strategy_agent_01_htf_timeframe": "H4",
            "strategy_agent_01_adx_min": "0.5",
            "strategy_agent_01_confirm_bars": "2",
            "strategy_agent_02_lookbacks": "10,20",
            "strategy_agent_02_entry_threshold": "0.02",
            "strategy_agent_02_vol_lookback": "14",
            "strategy_agent_02_max_hold_bars": "20",
            "strategy_agent_02_expiry_bars": "5",
            "strategy_agent_03_channel_bars": "20",
            "strategy_agent_03_buffer_ticks": "2",
            "strategy_agent_03_confirm_bars": "2",
            "strategy_agent_03_exit_bars": "10",
            "strategy_agent_04_vol_lookback": "14",
            "strategy_agent_04_compression_pctile": "0.25",
            "strategy_agent_04_confirm_bars": "2",
            "strategy_agent_05_trend_period": "50",
            "strategy_agent_05_pullback_ma": "10",
            "strategy_agent_05_confirm_bars": "2",
            "strategy_agent_05_expiry_bars": "5",
            "strategy_agent_06_session_name": "london",
            "strategy_agent_06_session_tz": "UTC",
            "strategy_agent_06_range_minutes": "120",
            "strategy_agent_06_buffer_ticks": "2",
            "strategy_agent_06_expiry_minutes": "480",
            "strategy_agent_06_max_spread_ticks": "5",
            "strategy_agent_07_basis_period": "5",
            "strategy_agent_07_band_width": "1.0",
            "strategy_agent_07_z_min": "1.0",
            "strategy_agent_07_rsi_period": "5",
            "strategy_agent_07_rsi_extreme": "30",
            "strategy_agent_07_confirm_bars": "1",
            "strategy_agent_08_session_name": "london",
            "strategy_agent_08_session_tz": "UTC",
            "strategy_agent_08_band_sigmas": "1.0",
            "strategy_agent_08_min_volume_bars": "5",
            "strategy_agent_09_swing_bars": "2",
            "strategy_agent_09_equal_tol_ticks": "2",
            "strategy_agent_09_sweep_tol_ticks": "2",
            "strategy_agent_09_disp_body_min_atr": "1.0",
            "strategy_agent_09_expiry_bars": "5",
            "strategy_agent_10_max_data_age_hours": "24",
            "strategy_agent_10_min_history_points": "50",
        }
    )
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


def test_phase3_policy_keys_fail_closed(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-3.1/D-3.2/D-36: a non-locked rounding mode or non-positive limit names its key."""
    from pydantic import ValidationError as PydanticValidationError

    monkeypatch.setenv("GOLDMASTERS_TICK_ROUNDING_MODE", "HALF_EVEN")
    with pytest.raises(PydanticValidationError, match="tick_rounding_mode"):
        Settings()  # type: ignore[call-arg]
    monkeypatch.delenv("GOLDMASTERS_TICK_ROUNDING_MODE")
    for key in ("MAX_RISK_PERCENT_PER_IDEA", "MIN_RISK_REWARD_RATIO"):
        monkeypatch.setenv(f"GOLDMASTERS_{key}", "0")
        with pytest.raises(PydanticValidationError, match=key.lower()):
            Settings()  # type: ignore[call-arg]
        monkeypatch.delenv(f"GOLDMASTERS_{key}")


def test_strategy_scaffold_fail_closed(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """03.1-01: scaffold rows default disabled/none/unset; bad members name the key."""
    from pydantic import ValidationError as PydanticValidationError

    settings = Settings()  # type: ignore[call-arg]
    assert settings.strategy_agent_01_enabled is False
    assert settings.strategy_agent_01_instruments == []
    assert settings.strategy_agent_01_timeframes == []
    assert settings.strategy_agent_01_regimes == []
    assert settings.strategy_agent_01_min_bars is None
    monkeypatch.setenv("GOLDMASTERS_STRATEGY_AGENT_01_TIMEFRAMES", "H1,NOPE")
    with pytest.raises(PydanticValidationError, match="strategy_agent_01_timeframes"):
        Settings()  # type: ignore[call-arg]
    monkeypatch.delenv("GOLDMASTERS_STRATEGY_AGENT_01_TIMEFRAMES")
    monkeypatch.setenv("GOLDMASTERS_STRATEGY_AGENT_01_REGIMES", "sideways")
    with pytest.raises(PydanticValidationError, match="strategy_agent_01_regimes"):
        Settings()  # type: ignore[call-arg]
    monkeypatch.delenv("GOLDMASTERS_STRATEGY_AGENT_01_REGIMES")
    monkeypatch.setenv("GOLDMASTERS_STRATEGY_AGENT_01_MIN_BARS", "0")
    with pytest.raises(PydanticValidationError, match="strategy_agent_01_min_bars"):
        Settings()  # type: ignore[call-arg]
    monkeypatch.delenv("GOLDMASTERS_STRATEGY_AGENT_01_MIN_BARS")
    assert _settings(
        monkeypatch, strategy_agent_01_instruments="xauusd, eurusd"
    ).strategy_agent_01_instruments == ["xauusd", "eurusd"]


def test_strategy_numeric_params_fail_closed(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """03.2-01: rule numerics default unset/empty; bad members name the key."""
    from pydantic import ValidationError as PydanticValidationError

    settings = Settings()  # type: ignore[call-arg]
    assert settings.strategy_agent_01_fast_period is None
    assert settings.strategy_agent_01_htf_timeframe is None
    assert settings.strategy_agent_01_adx_min is None
    assert settings.strategy_agent_02_lookbacks == []
    assert settings.strategy_agent_02_entry_threshold is None
    assert settings.strategy_agent_03_channel_bars is None
    assert settings.strategy_agent_04_compression_pctile is None
    assert settings.strategy_agent_05_trend_period is None
    assert settings.strategy_agent_06_session_name is None
    assert settings.strategy_agent_06_range_minutes is None
    assert settings.strategy_agent_07_basis_period is None
    assert settings.strategy_agent_07_band_width is None
    assert settings.strategy_agent_08_band_sigmas is None
    assert settings.strategy_agent_08_min_volume_bars is None
    assert settings.strategy_agent_09_swing_bars is None
    assert settings.strategy_agent_09_equal_tol_ticks is None
    assert settings.strategy_agent_09_sweep_tol_ticks is None
    assert settings.strategy_agent_09_disp_body_min_atr is None
    assert settings.strategy_agent_09_expiry_bars is None
    assert settings.strategy_agent_10_max_data_age_hours is None
    assert settings.strategy_agent_10_min_history_points is None
    assert _settings(
        monkeypatch, strategy_agent_02_lookbacks="10, 20"
    ).strategy_agent_02_lookbacks == [10, 20]
    assert (
        _settings(monkeypatch, strategy_agent_01_htf_timeframe="H4").strategy_agent_01_htf_timeframe
        == "H4"
    )
    for key, bad in (
        ("GOLDMASTERS_STRATEGY_AGENT_01_FAST_PERIOD", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_01_ADX_MIN", "-0.5"),
        ("GOLDMASTERS_STRATEGY_AGENT_02_LOOKBACKS", "10,0"),
        ("GOLDMASTERS_STRATEGY_AGENT_02_LOOKBACKS", "ten"),
        ("GOLDMASTERS_STRATEGY_AGENT_02_ENTRY_THRESHOLD", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_03_BUFFER_TICKS", "-2"),
        ("GOLDMASTERS_STRATEGY_AGENT_04_COMPRESSION_PCTILE", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_05_PULLBACK_MA", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_06_RANGE_MINUTES", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_06_BUFFER_TICKS", "-2"),
        ("GOLDMASTERS_STRATEGY_AGENT_07_BAND_WIDTH", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_07_RSI_EXTREME", "-30"),
        ("GOLDMASTERS_STRATEGY_AGENT_08_BAND_SIGMAS", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_08_MIN_VOLUME_BARS", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_09_SWING_BARS", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_09_EQUAL_TOL_TICKS", "-2"),
        ("GOLDMASTERS_STRATEGY_AGENT_09_SWEEP_TOL_TICKS", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_09_DISP_BODY_MIN_ATR", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_09_EXPIRY_BARS", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_10_MAX_DATA_AGE_HOURS", "0"),
        ("GOLDMASTERS_STRATEGY_AGENT_10_MIN_HISTORY_POINTS", "0"),
    ):
        monkeypatch.setenv(key, bad)
        with pytest.raises(PydanticValidationError, match=key.split("GOLDMASTERS_")[1].lower()):
            Settings()  # type: ignore[call-arg]
        monkeypatch.delenv(key)


def test_hash_covers_phase3_policy_keys(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-3.1: every new policy key joins the hashed config; empty reads as unset."""
    from goldmasters_api.settings import hash_effective_config

    baseline = hash_effective_config(_settings(monkeypatch))
    assert _settings(monkeypatch).tick_rounding_mode == "ROUND_HALF_UP"
    # tick_rounding_mode admits no other value, so its coverage is shown by
    # presence in the hashed payload: the placeholders move the digest.
    assert (
        hash_effective_config(_settings(monkeypatch, max_risk_percent_per_idea="1.0")) != baseline
    )
    assert hash_effective_config(_settings(monkeypatch, min_risk_reward_ratio="2.0")) != baseline
    assert _settings(monkeypatch, max_risk_percent_per_idea="").max_risk_percent_per_idea is None
