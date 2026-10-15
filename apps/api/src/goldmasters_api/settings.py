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
from typing import Annotated, Any

from goldmasters_contracts import IanaTimezone, ProviderId, Timeframe, TrendRegime
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

#: Version of the hash canonicalisation. Bumping this changes every digest by
#: construction, so a canonicalisation change is detectable, never silent.
HASH_ALGORITHM_VERSION = "1"


def _split_strategy_list(value: Any) -> Any:
    """Comma-separated env text reads as a list; empty/unset reads as none.

    Lists arrive via ``GOLDMASTERS_STRATEGY_AGENT_<NN>_*`` variables, where a
    bare ``.env`` template carries the empty string. An empty list means
    none (never "all" by default) so the eligibility matrix stays
    fail-closed. Non-string sequences pass through for item validation.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


#: Comma-separated instrument ids; empty means none.
#: ``NoDecode`` keeps the raw env text for the comma split (pydantic-settings
#: would otherwise demand JSON for a complex field).
CsvInstruments = Annotated[list[str], NoDecode, BeforeValidator(_split_strategy_list)]

#: Comma-separated canonical timeframes; unknown members fail startup.
CsvTimeframes = Annotated[list[Timeframe], NoDecode, BeforeValidator(_split_strategy_list)]

#: Comma-separated regime labels; unknown members fail startup.
CsvRegimes = Annotated[list[TrendRegime], NoDecode, BeforeValidator(_split_strategy_list)]


def _empty_min_bars_means_unset(value: Any) -> Any:
    """An empty template entry reads as unset, never as zero (D-3.1)."""
    if value == "":
        return None
    return value


def _min_bars_positive_or_unset(value: int | None) -> int | None:
    """Fail closed on a non-positive minimum bar count (D-3.1, D-36)."""
    if value is not None and (isinstance(value, bool) or value < 1):
        raise ValueError("strategy min_bars must be a positive int when set")
    return value


#: Minimum-bar placeholder: None blocks, never defaults (D-3.1).
FailClosedMinBars = Annotated[
    int | None,
    BeforeValidator(_empty_min_bars_means_unset),
    AfterValidator(_min_bars_positive_or_unset),
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
    # Phase 2 D-59 market-data keys (02-RESEARCH.md §5). All non-secret, so all
    # join the hashed effective config automatically. No GOLDMASTERS_MT5_*
    # secret field exists by design (D-47: bare attach, never credentials).
    provider_id: ProviderId = "mt5"
    instrument_id: str = "xauusd"
    mt5_symbol: str = "XAUUSD"
    timeframe: Timeframe = Timeframe.H1
    # Required, no default: startup fails closed naming this key until the
    # operator sets the broker server zone (02-RESEARCH.md §1).
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
    # Session windows (UTC, standard-time basis; DST ±1h is operator-confirmed
    # against the broker per D-57 — retune here, never in code). Off-hours is
    # whatever remains; the weekend window short-circuits thresholds entirely.
    session_overlap_utc: str = "13:00-16:30"
    session_major_utc: str = "08:00-13:00,16:30-21:00"
    session_asia_utc: str = "00:00-08:00"
    weekend_close_utc: str = "Fri 21:00-Sun 22:00"
    daily_break_utc: str = "21:00-22:00"

    # Phase 3 D-3.1/D-3.2 policy keys. The rounding mode is an operator
    # acknowledgement of the locked ROUND_HALF_UP (anything else fails
    # closed); the risk placeholders stay None until a strategy set is
    # approved — no threshold literal lives in code.
    tick_rounding_mode: str = "ROUND_HALF_UP"
    max_risk_percent_per_idea: float | None = None
    min_risk_reward_ratio: float | None = None

    # Phase 3.1 strategy-agent scaffold (03.1-RESEARCH.md locked shape). One
    # five-field row per agent (ENABLED flag, instrument list, timeframe
    # list, regime list, min_bars); every row is fail-closed until the
    # operator sets it — disabled, empty (none, never all), None (blocks).
    # Numeric rule params stay per-agent-phase (operator spec), never here.
    strategy_agent_01_enabled: bool = False
    strategy_agent_01_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_01_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_01_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_01_min_bars: FailClosedMinBars = None
    strategy_agent_02_enabled: bool = False
    strategy_agent_02_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_02_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_02_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_02_min_bars: FailClosedMinBars = None
    strategy_agent_03_enabled: bool = False
    strategy_agent_03_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_03_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_03_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_03_min_bars: FailClosedMinBars = None
    strategy_agent_04_enabled: bool = False
    strategy_agent_04_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_04_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_04_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_04_min_bars: FailClosedMinBars = None
    strategy_agent_05_enabled: bool = False
    strategy_agent_05_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_05_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_05_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_05_min_bars: FailClosedMinBars = None
    strategy_agent_06_enabled: bool = False
    strategy_agent_06_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_06_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_06_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_06_min_bars: FailClosedMinBars = None
    strategy_agent_07_enabled: bool = False
    strategy_agent_07_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_07_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_07_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_07_min_bars: FailClosedMinBars = None
    strategy_agent_08_enabled: bool = False
    strategy_agent_08_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_08_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_08_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_08_min_bars: FailClosedMinBars = None
    strategy_agent_09_enabled: bool = False
    strategy_agent_09_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_09_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_09_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_09_min_bars: FailClosedMinBars = None
    strategy_agent_10_enabled: bool = False
    strategy_agent_10_instruments: CsvInstruments = Field(default_factory=list)
    strategy_agent_10_timeframes: CsvTimeframes = Field(default_factory=list)
    strategy_agent_10_regimes: CsvRegimes = Field(default_factory=list)
    strategy_agent_10_min_bars: FailClosedMinBars = None

    @field_validator("session_overlap_utc", "session_major_utc", "session_asia_utc", mode="after")
    @classmethod
    def _window_specs_parse(cls, value: str) -> str:
        """Fail closed on a malformed session window (D-36, D-59)."""
        from services.mt5_adapter.validation import parse_session_windows

        parse_session_windows(value)
        return value

    @field_validator("weekend_close_utc", mode="after")
    @classmethod
    def _weekend_spec_parses(cls, value: str) -> str:
        """Fail closed on a malformed weekend window (D-36, D-58)."""
        from services.mt5_adapter.validation import parse_weekend_window

        parse_weekend_window(value)
        return value

    @field_validator("daily_break_utc", mode="after")
    @classmethod
    def _break_spec_parses(cls, value: str) -> str:
        """Fail closed on a malformed daily-break window (D-36, D-58)."""
        from services.mt5_adapter.validation import parse_daily_window

        parse_daily_window(value)
        return value

    @field_validator("tick_rounding_mode", mode="after")
    @classmethod
    def _rounding_mode_acknowledged(cls, value: str) -> str:
        """Fail closed unless the operator acknowledges the locked mode (D-3.2)."""
        if value != "ROUND_HALF_UP":
            raise ValueError(f"tick_rounding_mode {value!r} is not the locked D-3.2 mode")
        return value

    @field_validator("max_risk_percent_per_idea", "min_risk_reward_ratio", mode="before")
    @classmethod
    def _empty_placeholder_means_unset(cls, value: Any) -> Any:
        """An empty template entry reads as unset, never as zero (D-3.1)."""
        if value == "":
            return None
        return value

    @field_validator("max_risk_percent_per_idea", "min_risk_reward_ratio", mode="after")
    @classmethod
    def _risk_placeholders_positive(cls, value: float | None) -> float | None:
        """Fail closed on a non-positive risk placeholder (D-3.1, D-36)."""
        import math

        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError("risk placeholder must be finite and positive when set")
        return value

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
