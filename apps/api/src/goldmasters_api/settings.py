"""Typed settings resolved once at startup (D-15/D-27/D-36)."""

from __future__ import annotations

import hashlib
import json
import os
import typing
from decimal import Decimal
from typing import Annotated, Any
from urllib.parse import urlparse

from goldmasters_contracts import IanaTimezone, PriceStr, ProviderId, Timeframe, TrendRegime
from goldmasters_contracts.backtest import CostProfile
from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

__all__ = ["HASH_ALGORITHM_VERSION", "Settings", "hash_effective_config"]

HASH_ALGORITHM_VERSION = "1"


def _split_strategy_list(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CsvInstruments = Annotated[list[str], NoDecode, BeforeValidator(_split_strategy_list)]
CsvTimeframes = Annotated[list[Timeframe], NoDecode, BeforeValidator(_split_strategy_list)]
CsvRegimes = Annotated[list[TrendRegime], NoDecode, BeforeValidator(_split_strategy_list)]


def _empty_min_bars_means_unset(value: Any) -> Any:
    if value == "":
        return None
    return value


def _min_bars_positive_or_unset(value: int | None) -> int | None:
    if value is not None and (isinstance(value, bool) or value < 1):
        raise ValueError("strategy min_bars must be a positive int when set")
    return value


FailClosedMinBars = Annotated[
    int | None,
    BeforeValidator(_empty_min_bars_means_unset),
    AfterValidator(_min_bars_positive_or_unset),
]


def _count_positive_or_unset(value: int | None) -> int | None:
    if value is not None and (isinstance(value, bool) or value < 1):
        raise ValueError("strategy rule count must be a positive int when set")
    return value


FailClosedCount = Annotated[
    int | None,
    BeforeValidator(_empty_min_bars_means_unset),
    AfterValidator(_count_positive_or_unset),
]


def _decimal_positive_or_unset(value: Decimal | None) -> Decimal | None:
    if value is not None and value <= 0:
        raise ValueError("strategy rule threshold must be positive when set")
    return value


FailClosedDecimal = Annotated[
    Decimal | None,
    BeforeValidator(_empty_min_bars_means_unset),
    AfterValidator(_decimal_positive_or_unset),
]

FailClosedText = Annotated[
    str | None,
    BeforeValidator(_empty_min_bars_means_unset),
]


def _split_positive_int_list(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        try:
            parsed = [int(item) for item in items]
        except ValueError as err:
            raise ValueError(f"expected comma-separated positive ints, got {value!r}") from err
        value = parsed
    else:
        value = list(value)
    if any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in value):
        raise ValueError(f"expected comma-separated positive ints, got {value!r}")
    return value


CsvPositiveInts = Annotated[list[int], NoDecode, BeforeValidator(_split_positive_int_list)]


def _parse_cost_profiles(value: Any) -> dict[str, CostProfile]:
    """Parse a JSON object of instrument_id -> cost profile mapping."""
    if value is None or value == "":
        return {}
    if isinstance(value, str):
        import json

        raw = json.loads(value)
        return {k: CostProfile(**v) for k, v in raw.items()}
    return value


CostProfiles = Annotated[
    dict[str, CostProfile], NoDecode, BeforeValidator(_parse_cost_profiles)
]


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
    provider_id: ProviderId = "mt5"
    instrument_id: str = "xauusd"
    mt5_symbol: str = "XAUUSD"
    timeframe: Timeframe = Timeframe.H1
    mt5_server_timezone: IanaTimezone
    mt5_probe_timeout_seconds: float = 2.0
    mt5_retry_attempts: int = 1
    mt5_retry_delay_ms: int = 500
    mt5_bars_count: int = 10
    bar_stale_closed_bars: int = 2
    bar_stale_grace_seconds: int = 300
    quote_stale_seconds_overlap: int = 30
    quote_stale_seconds_major: int = 60
    quote_stale_seconds_asia: int = 180
    quote_stale_seconds_offhours: int = 300
    session_overlap_utc: str = "13:00-16:30"
    session_major_utc: str = "08:00-13:00,16:30-21:00"
    session_asia_utc: str = "00:00-08:00"
    weekend_close_utc: str = "Fri 21:00-Sun 22:00"
    daily_break_utc: str = "21:00-22:00"

    tick_rounding_mode: str = "ROUND_HALF_UP"
    max_risk_percent_per_idea: float | None = None
    min_risk_reward_ratio: float | None = None

    strategy_agent_01_enabled: bool = False
    strategy_agent_01_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_01_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_01_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_01_min_bars: FailClosedMinBars = None
    strategy_agent_01_fast_period: FailClosedCount = None
    strategy_agent_01_slow_period: FailClosedCount = None
    strategy_agent_01_htf_timeframe: FailClosedText = None
    strategy_agent_01_adx_min: FailClosedDecimal = None
    strategy_agent_01_confirm_bars: FailClosedCount = None
    strategy_agent_02_enabled: bool = False
    strategy_agent_02_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_02_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_02_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_02_min_bars: FailClosedMinBars = None
    strategy_agent_02_lookbacks: CsvPositiveInts = Field(default_factory=list)
    strategy_agent_02_entry_threshold: FailClosedDecimal = None
    strategy_agent_02_vol_lookback: FailClosedCount = None
    strategy_agent_02_max_hold_bars: FailClosedCount = None
    strategy_agent_02_expiry_bars: FailClosedCount = None
    strategy_agent_03_enabled: bool = False
    strategy_agent_03_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_03_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_03_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_03_min_bars: FailClosedMinBars = None
    strategy_agent_03_channel_bars: FailClosedCount = None
    strategy_agent_03_buffer_ticks: FailClosedCount = None
    strategy_agent_03_confirm_bars: FailClosedCount = None
    strategy_agent_03_exit_bars: FailClosedCount = None
    strategy_agent_04_enabled: bool = False
    strategy_agent_04_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_04_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_04_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_04_min_bars: FailClosedMinBars = None
    strategy_agent_04_vol_lookback: FailClosedCount = None
    strategy_agent_04_compression_pctile: FailClosedDecimal = None
    strategy_agent_04_confirm_bars: FailClosedCount = None
    strategy_agent_05_enabled: bool = False
    strategy_agent_05_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_05_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_05_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_05_min_bars: FailClosedMinBars = None
    strategy_agent_05_trend_period: FailClosedCount = None
    strategy_agent_05_pullback_ma: FailClosedCount = None
    strategy_agent_05_confirm_bars: FailClosedCount = None
    strategy_agent_05_expiry_bars: FailClosedCount = None
    strategy_agent_06_enabled: bool = False
    strategy_agent_06_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_06_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_06_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_06_min_bars: FailClosedMinBars = None
    strategy_agent_06_session_name: FailClosedText = None
    strategy_agent_06_session_tz: FailClosedText = None
    strategy_agent_06_range_minutes: FailClosedCount = None
    strategy_agent_06_buffer_ticks: FailClosedCount = None
    strategy_agent_06_expiry_minutes: FailClosedCount = None
    strategy_agent_06_max_spread_ticks: FailClosedCount = None
    strategy_agent_07_enabled: bool = False
    strategy_agent_07_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_07_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_07_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_07_min_bars: FailClosedMinBars = None
    strategy_agent_07_basis_period: FailClosedCount = None
    strategy_agent_07_band_width: FailClosedDecimal = None
    strategy_agent_07_z_min: FailClosedDecimal = None
    strategy_agent_07_rsi_period: FailClosedCount = None
    strategy_agent_07_rsi_extreme: FailClosedDecimal = None
    strategy_agent_07_confirm_bars: FailClosedCount = None
    strategy_agent_08_enabled: bool = False
    strategy_agent_08_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_08_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_08_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_08_min_bars: FailClosedMinBars = None
    strategy_agent_08_session_name: FailClosedText = None
    strategy_agent_08_session_tz: FailClosedText = None
    strategy_agent_08_band_sigmas: FailClosedDecimal = None
    strategy_agent_08_min_volume_bars: FailClosedCount = None
    strategy_agent_09_enabled: bool = False
    strategy_agent_09_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_09_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_09_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_09_min_bars: FailClosedMinBars = None
    strategy_agent_09_swing_bars: FailClosedCount = None
    strategy_agent_09_equal_tol_ticks: FailClosedCount = None
    strategy_agent_09_sweep_tol_ticks: FailClosedCount = None
    strategy_agent_09_disp_body_min_atr: FailClosedDecimal = None
    strategy_agent_09_expiry_bars: FailClosedCount = None
    strategy_agent_10_enabled: bool = False
    strategy_agent_10_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_10_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_10_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_10_min_bars: FailClosedMinBars = None
    strategy_agent_10_max_data_age_hours: FailClosedDecimal = None
    strategy_agent_10_min_history_points: FailClosedCount = None

    graph_node_timeout_seconds: float = 60.0
    graph_node_max_retries: int = 2
    graph_max_concurrency: int | None = None

    # --- Cost configuration (Phase 6). All fields are optional and fail-closed:
    # None means unconfigured; an explicitly configured zero cost is Decimal("0").
    cost_spread: PriceStr | None = None
    cost_commission: PriceStr | None = None
    cost_slippage: PriceStr | None = None
    cost_swap: PriceStr | None = None
    # Instrument-specific cost profiles, keyed by instrument_id. JSON-encoded
    # mapping of instrument_id -> {spread, commission, slippage, swap, confirmed}.
    cost_profiles: CostProfiles = Field(default_factory=dict)

    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: FailClosedText = None

    @field_validator("session_overlap_utc", "session_major_utc", "session_asia_utc", mode="after")
    @classmethod
    def _window_specs_parse(cls, value: str) -> str:
        from services.mt5_adapter.validation import parse_session_windows

        parse_session_windows(value)
        return value

    @field_validator("weekend_close_utc", mode="after")
    @classmethod
    def _weekend_spec_parses(cls, value: str) -> str:
        from services.mt5_adapter.validation import parse_weekend_window

        parse_weekend_window(value)
        return value

    @field_validator("daily_break_utc", mode="after")
    @classmethod
    def _break_spec_parses(cls, value: str) -> str:
        from services.mt5_adapter.validation import parse_daily_window

        parse_daily_window(value)
        return value

    @field_validator("tick_rounding_mode", mode="after")
    @classmethod
    def _rounding_mode_acknowledged(cls, value: str) -> str:
        if value != "ROUND_HALF_UP":
            raise ValueError(f"tick_rounding_mode {value!r} is not the locked D-3.2 mode")
        return value

    @field_validator("max_risk_percent_per_idea", "min_risk_reward_ratio", mode="before")
    @classmethod
    def _empty_placeholder_means_unset(cls, value: Any) -> Any:
        if value == "":
            return None
        return value

    @field_validator("max_risk_percent_per_idea", "min_risk_reward_ratio", mode="after")
    @classmethod
    def _risk_placeholders_positive(cls, value: float | None) -> float | None:
        import math

        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError("risk placeholder must be finite and positive when set")
        return value

    @field_validator("graph_node_timeout_seconds", mode="before")
    @classmethod
    def _graph_timeout_empty_means_default(cls, value: Any) -> Any:
        if value == "":
            return 60.0
        return value

    @field_validator("graph_node_timeout_seconds", mode="after")
    @classmethod
    def _graph_timeout_positive(cls, value: float) -> float:
        import math

        if not math.isfinite(value) or value <= 0:
            raise ValueError("graph_node_timeout_seconds must be finite and positive")
        return value

    @field_validator("graph_node_max_retries", mode="before")
    @classmethod
    def _graph_retries_empty_means_default(cls, value: Any) -> Any:
        if value == "":
            return 2
        return value

    @field_validator("graph_node_max_retries", mode="after")
    @classmethod
    def _graph_retries_non_negative(cls, value: int) -> int:
        if isinstance(value, bool) or value < 0:
            raise ValueError("graph_node_max_retries must be a non-negative int")
        return value

    @field_validator("graph_max_concurrency", mode="before")
    @classmethod
    def _graph_concurrency_empty_means_unset(cls, value: Any) -> Any:
        if value == "":
            return None
        return value

    @field_validator("graph_max_concurrency", mode="after")
    @classmethod
    def _graph_concurrency_positive_or_unset(cls, value: int | None) -> int | None:
        if value is not None and (isinstance(value, bool) or value < 1):
            raise ValueError("graph_max_concurrency must be a positive int when set")
        return value

    @field_validator(
        "cost_spread",
        "cost_commission",
        "cost_slippage",
        "cost_swap",
        mode="before",
    )
    @classmethod
    def _cost_empty_means_unset(cls, value: Any) -> Any:
        if value == "":
            return None
        return value

    @field_validator("cost_spread", "cost_commission", "cost_slippage", "cost_swap")
    @classmethod
    def _cost_positive_or_unset(cls, value: Decimal | None) -> Decimal | None:
        import math

        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError("cost value must be finite and positive when set")
        return value

    @field_validator("ollama_host", mode="before")
    @classmethod
    def _ollama_host_empty_means_default(cls, value: Any) -> Any:
        if value == "":
            return "http://127.0.0.1:11434"
        return value

    @field_validator("ollama_host", mode="after")
    @classmethod
    def _ollama_host_loopback_only(cls, value: str) -> str:
        if urlparse(value).scheme not in ("http", "https") or urlparse(value).hostname not in (
            "127.0.0.1",
            "::1",
            "localhost",
        ):
            raise ValueError(f"ollama_host {value!r} is not a loopback endpoint")
        return value

    @model_validator(mode="before")
    @classmethod
    def _reject_undeclared_prefixed_variables(cls, data: Any) -> Any:
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
    """Hash the canonical JSON of the non-secret settings (sha256 hex)."""
    payload = {
        key: value
        for key, value in settings.model_dump().items()
        if not _is_secret_field(settings, key)
    }
    payload["_hash_algorithm_version"] = HASH_ALGORITHM_VERSION
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
