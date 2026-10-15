"""MT5 read-only adapter over the :class:`TerminalGateway` protocol (D-44..D-55).

The adapter owns explicit selection (mapping table as data, never branches),
bare-attach with a read-only session assertion, one retry then disconnected
(D-51), exactly one ``last_error()`` capture per ``None`` return, and the
tracer C-09 error map. Gaps are flagged, never filled; an unsupported
instrument/timeframe answers ``UNSUPPORTED_INSTRUMENT`` /
``UNSUPPORTED_TIMEFRAME`` verbatim (typo locked, ``errors.py:30``) with no
gateway call and no substitution.

Terminal-field names (``trade_allowed``, ``select``/``visible``,
``digits``/``point``) come from the integration docs and are
must-verify-first against the installed package (RISK-03): presence is
asserted at runtime and absence fails the read visibly.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from goldmasters_contracts import (
    ErrorCode,
    MarketBar,
    MarketQuote,
    PrecisionRow,
    PrecisionTable,
    QualityStatus,
)

from services.mt5_adapter import normalize
from services.mt5_adapter.normalize import NormalizationError
from services.mt5_adapter.terminal import TerminalGateway
from services.mt5_adapter.validation import (
    quote_stale_limit_for,
    validate_bars,
    validate_quote,
    verdict_for_bars,
)

__all__ = [
    "AdapterFailure",
    "INSTRUMENT_SYMBOL_MAP",
    "PROVIDER_ID",
    "Mt5Adapter",
    "in_weekend_close",
    "probe_mt5",
]

#: Generic provider key (D-25 form, no broker suffix — D-48).
PROVIDER_ID = "mt5"

#: Canonical ``(instrument_id, timeframe)`` → provider symbol, as data (D-52/D-53).
#: Only gold/H1 ships; every other pair answers unsupported (D-54).
INSTRUMENT_SYMBOL_MAP: dict[tuple[str, str], str] = {("xauusd", "H1"): "XAUUSD"}

#: ``last_error`` codes that are never retried (bad args, no history,
#: session state, unsupported method — 02-RESEARCH.md §1 table).
_NO_RETRY_CODES: frozenset[int] = frozenset({-2, -4, -6, -7})

#: Sanity bound on the configured server zone vs the terminal clock
#: (02-RESEARCH.md §1). shortcut: fixed until it becomes a D-59 key (plan 02-02).
_OFFSET_TOLERANCE_SECONDS = 900

ProviderKind = Literal[
    "unsupported", "missing-history", "terminal-closed", "disconnected", "stale", "malformed"
]


@dataclass(frozen=True, slots=True)
class AdapterFailure:
    """Typed adapter failure: C-09 code for the API map plus provider kind for health."""

    code: ErrorCode
    kind: ProviderKind
    message: str


def _map_last_error(code: int) -> ProviderKind:
    """Map a ``last_error`` code per the 02-RESEARCH.md §1 table."""
    if code in (-2, -7):
        return "unsupported"
    if code == -4:
        return "missing-history"
    if code == -6:
        return "terminal-closed"
    return "disconnected"


def _failure_for(kind: ProviderKind, message: str) -> AdapterFailure:
    """Tracer C-09 map: transient reads retryable, quality reads not.

    ``missing-history``/``stale``/``malformed`` ride on ``CONFIG_INVALID``
    until plan 02-03 pins richer codes; retryability already points the right
    way (only transient ``INTERNAL_ERROR`` retries).
    """
    if kind in ("terminal-closed", "disconnected"):
        return AdapterFailure(ErrorCode.INTERNAL_ERROR, kind, message)
    if kind == "unsupported":
        return AdapterFailure(ErrorCode.UNSUPPORTED_INSTRUMENT, kind, message)
    return AdapterFailure(ErrorCode.CONFIG_INVALID, kind, message)


class Mt5Adapter:
    """Read-only MT5 adapter coding against :class:`TerminalGateway` only."""

    def __init__(
        self,
        gateway: TerminalGateway,
        *,
        server_timezone: str,
        retry_attempts: int = 1,
        retry_delay_ms: int = 500,
        bars_count: int = 10,
        bar_stale_closed_bars: int = 2,
        bar_stale_grace_seconds: int = 300,
        quote_overlap_seconds: int = 30,
        quote_major_seconds: int = 60,
        quote_asia_seconds: int = 180,
        quote_offhours_seconds: int = 300,
    ) -> None:
        self._gateway = gateway
        self._server_timezone = server_timezone
        self._retry_attempts = retry_attempts
        self._retry_delay_ms = retry_delay_ms
        self._bars_count = bars_count
        self._stale_closed_bars = bar_stale_closed_bars
        self._stale_grace_seconds = bar_stale_grace_seconds
        self._quote_limits = (quote_overlap_seconds, quote_major_seconds, quote_asia_seconds)
        self._quote_offhours = quote_offhours_seconds

    # -- selection (no gateway touch on failure) ---------------------------

    def _resolve(self, instrument_id: str, timeframe: str) -> str | AdapterFailure:
        """Map ``(instrument_id, timeframe)`` to the provider symbol, or fail."""
        symbol = INSTRUMENT_SYMBOL_MAP.get((instrument_id, timeframe))
        if symbol is not None:
            return symbol
        known_instruments = {key[0] for key in INSTRUMENT_SYMBOL_MAP}
        if instrument_id not in known_instruments:
            return AdapterFailure(
                ErrorCode.UNSUPPORTED_INSTRUMENT,
                "unsupported",
                f"instrument {instrument_id!r} is not mapped for provider mt5",
            )
        return AdapterFailure(
            ErrorCode.UNSUPPORTED_TIMEFRAME,
            "unsupported",
            f"timeframe {timeframe!r} is not supported for {instrument_id!r}",
        )

    def _resolve_symbol(self, instrument_id: str) -> str | AdapterFailure:
        """Map an instrument to its symbol for timeframe-free reads (quote/spec)."""
        for (known_instrument, _), symbol in INSTRUMENT_SYMBOL_MAP.items():
            if known_instrument == instrument_id:
                return symbol
        return AdapterFailure(
            ErrorCode.UNSUPPORTED_INSTRUMENT,
            "unsupported",
            f"instrument {instrument_id!r} is not mapped for provider mt5",
        )

    # -- session guards ----------------------------------------------------

    def _capture_error(self) -> ProviderKind:
        """Exactly one ``last_error()`` capture, mapped; never leaks payloads."""
        try:
            raw = self._gateway.last_error()
            code = int(raw[0])
        except Exception:  # noqa: BLE001 — any unreadable error reads disconnected
            return "disconnected"
        return _map_last_error(code)

    def _check_read_only(self) -> AdapterFailure | None:
        """Require an investor (read-only) session; a master session is refused."""
        try:
            terminal = self._gateway.terminal_info()
            account = self._gateway.account_info()
        except Exception:  # noqa: BLE001 — an unreadable session reads disconnected
            return _failure_for("disconnected", "mt5 session descriptors are unreadable")
        if terminal is None or not hasattr(terminal, "trade_allowed"):
            return _failure_for(
                "disconnected",
                "terminal descriptor lacks trade_allowed (must-verify-first, RISK-03)",
            )
        if account is None:
            return _failure_for("terminal-closed", "mt5 account is not attached")
        if bool(terminal.trade_allowed):
            return _failure_for(
                "terminal-closed", "terminal session is not read-only; refusing to proceed"
            )
        return None

    def _check_clock(self, server_epoch: Any, now_utc: datetime) -> AdapterFailure | None:
        """Refuse to stamp times when the terminal clock disagrees with the zone."""
        try:
            implied = float(server_epoch) - now_utc.timestamp()
            expected = ZoneInfo(self._server_timezone).utcoffset(now_utc)
            skew = abs(implied - expected.total_seconds()) if expected is not None else None
        except Exception:  # noqa: BLE001 — an unreadable clock reads disconnected
            return _failure_for("disconnected", "terminal clock is unreadable")
        if skew is None or skew > _OFFSET_TOLERANCE_SECONDS:
            return _failure_for(
                "disconnected", "terminal clock disagrees with the configured server zone"
            )
        return None

    def _attached(self) -> AdapterFailure | None:
        """Bare attach plus read-only assertion; ``None`` means ready."""
        try:
            attached = self._gateway.initialize()
        except Exception:  # noqa: BLE001 — attach failure is a value, never raises
            return _failure_for("terminal-closed", "mt5 terminal is not reachable")
        if not attached:
            kind = self._capture_error()
            if kind not in ("terminal-closed", "disconnected"):
                kind = "terminal-closed"
            return _failure_for(kind, "mt5 terminal is not reachable")
        return self._check_read_only()

    def _fetch_rows(
        self, symbol: str, timeframe: str, count: int
    ) -> list[dict[str, Any]] | AdapterFailure:
        """One quick retry (D-51), then disconnected; unsupported never retries."""
        attempts = 1 + max(0, self._retry_attempts)
        failure: AdapterFailure = _failure_for("disconnected", "mt5 read failed")
        for attempt in range(attempts):
            try:
                rows = self._gateway.copy_rates_from_pos(symbol, timeframe, 0, count + 1)
            except Exception:  # noqa: BLE001 — a raising terminal reads disconnected
                rows = None
            if rows is not None:
                return rows
            kind = self._capture_error()
            failure = _failure_for(kind, "mt5 bars read failed")
            if kind in ("unsupported", "missing-history", "terminal-closed"):
                return failure
            if attempt + 1 < attempts:
                time.sleep(self._retry_delay_ms / 1000.0)
        return failure

    # -- reads -------------------------------------------------------------

    def get_bars(
        self,
        instrument_id: str,
        timeframe: str,
        *,
        count: int | None = None,
        now_utc: datetime | None = None,
        precision_table: PrecisionTable | None = None,
    ) -> tuple[MarketBar, ...] | AdapterFailure:
        """Closed H1 bars with provenance and quality; never a substituted symbol."""
        resolved = self._resolve(instrument_id, timeframe)
        if isinstance(resolved, AdapterFailure):
            return resolved
        wanted = self._bars_count if count is None else count
        if wanted < 1:
            return AdapterFailure(ErrorCode.CONFIG_INVALID, "malformed", "bars count must be >= 1")
        now = now_utc or datetime.now(UTC)
        guard = self._attached()
        if guard is not None:
            return guard
        try:
            info = self._gateway.symbol_info(resolved)
            if info is None:
                return _failure_for("unsupported", f"symbol {resolved!r} is not exposed")
            if not getattr(info, "visible", False):
                return _failure_for(
                    "unsupported", f"symbol {resolved!r} is not enabled for reading"
                )
            clock_guard = self._check_clock(getattr(info, "time", None), now)
            if clock_guard is not None:
                return clock_guard
            rows = self._fetch_rows(resolved, timeframe, wanted)
            if isinstance(rows, AdapterFailure):
                return rows
            if len(rows) <= 1:
                return _failure_for("missing-history", "terminal returned no closed bars")
            try:
                bars = normalize.normalize_bars(
                    rows,
                    instrument_id=instrument_id,
                    provider_symbol=resolved,
                    timeframe=timeframe,
                    server_timezone=self._server_timezone,
                    retrieved_at=now,
                )
            except NormalizationError as exc:
                return AdapterFailure(ErrorCode.CONFIG_INVALID, "malformed", str(exc))
            return tuple(
                validate_bars(
                    bars,
                    now_utc=now,
                    stale_closed_bars=self._stale_closed_bars,
                    stale_grace_seconds=self._stale_grace_seconds,
                    precision_table=precision_table,
                )
            )
        finally:
            self._gateway.shutdown()

    def get_latest_quote(
        self, instrument_id: str, *, now_utc: datetime | None = None
    ) -> MarketQuote | AdapterFailure:
        """Latest bid/ask tick; ``last=0.0`` maps to ``None``, never ``0.0``."""
        resolved = self._resolve_symbol(instrument_id)
        if isinstance(resolved, AdapterFailure):
            return resolved
        now = now_utc or datetime.now(UTC)
        guard = self._attached()
        if guard is not None:
            return guard
        try:
            attempts = 1 + max(0, self._retry_attempts)
            tick: dict[str, Any] | None = None
            failure = _failure_for("disconnected", "mt5 tick read failed")
            for attempt in range(attempts):
                try:
                    tick = self._gateway.symbol_info_tick(resolved)
                except Exception:  # noqa: BLE001 — a raising terminal reads disconnected
                    tick = None
                if tick is not None:
                    break
                kind = self._capture_error()
                failure = _failure_for(kind, "mt5 tick read failed")
                if kind in ("unsupported", "missing-history", "terminal-closed"):
                    return failure
                if attempt + 1 < attempts:
                    time.sleep(self._retry_delay_ms / 1000.0)
            if tick is None:
                return failure
            try:
                quote = normalize.normalize_quote(
                    tick,
                    instrument_id=instrument_id,
                    provider_symbol=resolved,
                    server_timezone=self._server_timezone,
                    retrieved_at=now,
                )
            except NormalizationError as exc:
                return AdapterFailure(ErrorCode.CONFIG_INVALID, "malformed", str(exc))
            overlap, major, asia = self._quote_limits
            limit = quote_stale_limit_for(
                now, overlap=overlap, major=major, asia=asia, offhours=self._quote_offhours
            )
            return validate_quote(quote, now_utc=now, stale_seconds=limit)
        finally:
            self._gateway.shutdown()

    def get_instrument_spec(
        self, instrument_id: str, *, now_utc: datetime | None = None
    ) -> PrecisionRow | AdapterFailure:
        """Precision spec; the caller appends via ``PrecisionTable.with_row``."""
        resolved = self._resolve_symbol(instrument_id)
        if isinstance(resolved, AdapterFailure):
            return resolved
        now = now_utc or datetime.now(UTC)
        guard = self._attached()
        if guard is not None:
            return guard
        try:
            info = self._gateway.symbol_info(resolved)
            if info is None or not getattr(info, "visible", False):
                return _failure_for("unsupported", f"symbol {resolved!r} is not exposed")
            for field in ("digits", "point"):
                if getattr(info, field, None) is None:
                    return _failure_for(
                        "disconnected",
                        f"symbol descriptor lacks {field} (must-verify-first, RISK-03)",
                    )
            try:
                version = self._gateway.version()
                build = version[1] if version is not None else "unknown"
            except Exception:  # noqa: BLE001 — build provenance degrades, read continues
                build = "unknown"
            try:
                return PrecisionRow(
                    instrument_id=instrument_id,
                    provider_id=PROVIDER_ID,
                    tick_size=str(info.point),
                    decimals=int(info.digits),
                    provider_spec_version=f"build {build}",
                    retrieved_at=now,
                    valid_from=now,
                )
            except Exception as exc:  # noqa: BLE001 — contract rejection reads malformed
                return AdapterFailure(ErrorCode.CONFIG_INVALID, "malformed", str(exc))
        finally:
            self._gateway.shutdown()

    def capabilities(self) -> dict[str, object]:
        """Supported vs unsupported mapping entries for the connected terminal."""
        try:
            self._gateway.initialize()  # attach only; readiness is proven by symbols_get below
        except Exception:  # noqa: BLE001 — capability probe never raises
            return {"provider_id": PROVIDER_ID, "supported": [], "unsupported": []}
        try:
            names: set[str] = set()
            try:
                symbols = self._gateway.symbols_get()
                for entry in symbols or []:
                    name = getattr(entry, "name", None)
                    if isinstance(name, str):
                        names.add(name)
            except Exception:  # noqa: BLE001 — capability probe never raises
                pass
            supported: list[dict[str, object]] = []
            unsupported: list[dict[str, object]] = []
            for (instrument_id, timeframe), symbol in INSTRUMENT_SYMBOL_MAP.items():
                entry = {
                    "instrument_id": instrument_id,
                    "provider_symbol": symbol,
                    "timeframes": [timeframe],
                }
                (supported if symbol in names else unsupported).append(entry)
            return {"provider_id": PROVIDER_ID, "supported": supported, "unsupported": unsupported}
        finally:
            try:
                self._gateway.shutdown()
            except Exception:  # noqa: BLE001 — capability probe never raises
                pass


def in_weekend_close(moment_utc: datetime) -> bool:
    """Weekend-close stub: Sat, Sun before 22:00 UTC, Fri from 21:00 UTC.

    Tracer approximation of ``GOLDMASTERS_WEEKEND_CLOSE_UTC``; the full
    calendar table is plan 02-02 detail (FLAGGED ASSUMPTION).
    """
    moment = moment_utc.astimezone(UTC)
    minutes = moment.hour * 60 + moment.minute
    if moment.weekday() == 5:
        return True
    if moment.weekday() == 6:
        return minutes < 22 * 60
    return moment.weekday() == 4 and minutes >= 21 * 60


def _provider_object(
    status: str,
    *,
    market_open: bool | None,
    terminal_build: str | None,
    last_bar_close_time: str | None,
    last_quote_time: str | None,
    checked_at: datetime,
) -> dict[str, object]:
    """Seven-key provider object; fixed shape, no terminal internals."""
    return {
        "provider_id": PROVIDER_ID,
        "status": status,
        "market_open": market_open,
        "terminal_build": terminal_build,
        "last_bar_close_time": last_bar_close_time,
        "last_quote_time": last_quote_time,
        "checked_at": checked_at.astimezone(UTC).isoformat(),
    }


def _probe_once(
    gateway: TerminalGateway, server_timezone: str, bars_count: int, now: datetime
) -> dict[str, object]:
    """Single bounded probe pass; every failure maps to a status, never raises."""
    adapter = Mt5Adapter(gateway, server_timezone=server_timezone, bars_count=bars_count)
    try:
        version = gateway.version()
        build = str(version[1]) if version is not None else None
    except Exception:  # noqa: BLE001 — probe contract: every failure maps to a status
        build = None
    bars = adapter.get_bars("xauusd", "H1", now_utc=now)
    if isinstance(bars, AdapterFailure):
        status = {
            "terminal-closed": "terminal-closed",
            "disconnected": "disconnected",
            "unsupported": "unsupported-symbol",
            "missing-history": "missing-history",
            "stale": "disconnected",
            "malformed": "disconnected",
        }[bars.kind]
        return _provider_object(
            status,
            market_open=None,
            terminal_build=build,
            last_bar_close_time=None,
            last_quote_time=None,
            checked_at=now,
        )
    failure_kind = verdict_for_bars(bars)
    quote = adapter.get_latest_quote("xauusd", now_utc=now)
    quote_time: str | None = None
    if isinstance(quote, MarketQuote):
        instant = quote.last_time or quote.ask_time or quote.bid_time
        quote_time = instant.astimezone(UTC).isoformat() if instant is not None else None
        if quote.quality_status != QualityStatus.OK:
            failure_kind = failure_kind or QualityStatus.STALE
    weekend = in_weekend_close(now)
    if failure_kind is not None and not weekend:
        return _provider_object(
            "disconnected",
            market_open=True,
            terminal_build=build,
            last_bar_close_time=bars[-1].bar_close_time.astimezone(UTC).isoformat()
            if bars[-1].bar_close_time is not None
            else None,
            last_quote_time=quote_time,
            checked_at=now,
        )
    return _provider_object(
        "connected",
        market_open=not weekend,
        terminal_build=build,
        last_bar_close_time=bars[-1].bar_close_time.astimezone(UTC).isoformat()
        if bars[-1].bar_close_time is not None
        else None,
        last_quote_time=quote_time,
        checked_at=now,
    )


def probe_mt5(
    gateway: TerminalGateway,
    *,
    server_timezone: str,
    timeout_seconds: float = 2.0,
    bars_count: int = 2,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Bounded provider probe for ``GET /health`` (follows ``probe_database``).

    Never raises and never leaks terminal internals: every exception maps to a
    ``disconnected`` object with the fixed seven-key shape.
    """
    now = now_utc or datetime.now(UTC)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_probe_once, gateway, server_timezone, bars_count, now)
            result = future.result(timeout=timeout_seconds)
            if isinstance(result, dict):
                return result
    except Exception:  # noqa: BLE001 — probe contract: every failure maps to a status
        pass
    return _provider_object(
        "disconnected",
        market_open=None,
        terminal_build=None,
        last_bar_close_time=None,
        last_quote_time=None,
        checked_at=now,
    )
