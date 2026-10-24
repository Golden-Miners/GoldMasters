"""MT5 read-only adapter over a persistent TerminalManager and SymbolResolver.

The adapter owns explicit selection (symbol resolution as data, never branches),
read-only session assertion, one retry then disconnected (D-51), exactly one
``last_error()`` capture per ``None`` return, and the tracer C-09 error map.
Gaps are flagged, never filled; an unsupported instrument/timeframe answers
``UNSUPPORTED_INSTRUMENT`` / ``UNSUPPORTED_TIMEFRAME`` verbatim with no
gateway call and no substitution.

Terminal-field names (``trade_allowed``, ``select``/``visible``,
``digits``/``point``) come from the integration docs and are
must-verify-first against the installed package (RISK-03): presence is
asserted at runtime and absence fails the read visibly.

The terminal IPC lifecycle is owned by ``TerminalManager`` — the adapter
never calls ``initialize()`` or ``shutdown()`` directly. The symbol
resolution is owned by ``SymbolResolver`` — the adapter never hardcodes
broker-specific symbols.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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
from services.mt5_adapter.symbol_resolver import (
    SymbolResolutionFailure,
    SymbolResolver,
)
from services.mt5_adapter.terminal import (
    CANONICAL_INSTRUMENT_IDS,
    TerminalManager,
)
from services.mt5_adapter.validation import (
    is_weekend_closed,
    missing_opens,
    quote_stale_limit_for,
    validate_bars,
    validate_quote,
    verdict_for_bars,
)

__all__ = [
    "AdapterFailure",
    "PROVIDER_ID",
    "Mt5Adapter",
    "probe_mt5",
]

#: Generic provider key (D-25 form, no broker suffix — D-48).
PROVIDER_ID = "mt5"

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


def _gap_spans(bars: Sequence[MarketBar]) -> list[tuple[datetime, datetime, list[datetime]]]:
    """One ``(start, end, missing-opens)`` span per bar stamped ``missing-history``."""
    spans: list[tuple[datetime, datetime, list[datetime]]] = []
    previous_open: datetime | None = None
    for bar in bars:
        if QualityStatus.MISSING_HISTORY in bar.quality_flags and previous_open is not None:
            missing = missing_opens(previous_open, bar.bar_open_time)
            spans.append((previous_open, bar.bar_open_time, missing))
        previous_open = bar.bar_open_time
    return spans


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
    """Read-only MT5 adapter over :class:`TerminalManager` and
    :class:`SymbolResolver`.

    Never calls ``initialize()`` or ``shutdown()`` directly — those are owned
    by ``TerminalManager``. Never hardcodes broker-specific symbols — those
    are resolved by ``SymbolResolver``.
    """

    def __init__(
        self,
        terminal_manager: TerminalManager,
        symbol_resolver: SymbolResolver,
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
        session_overlap_utc: str = "13:00-16:30",
        session_major_utc: str = "08:00-13:00,16:30-21:00",
        session_asia_utc: str = "00:00-08:00",
        weekend_close_utc: str = "Fri 21:00-Sun 22:00",
        daily_break_utc: str = "21:00-22:00",
    ) -> None:
        self._terminal_manager = terminal_manager
        self._symbol_resolver = symbol_resolver
        self._server_timezone = server_timezone
        self._retry_attempts = retry_attempts
        self._retry_delay_ms = retry_delay_ms
        self._bars_count = bars_count
        self._stale_closed_bars = bar_stale_closed_bars
        self._stale_grace_seconds = bar_stale_grace_seconds
        self._quote_limits = (quote_overlap_seconds, quote_major_seconds, quote_asia_seconds)
        self._quote_offhours = quote_offhours_seconds
        self._session_windows = (session_overlap_utc, session_major_utc, session_asia_utc)
        self._weekend_spec = weekend_close_utc
        self._break_spec = daily_break_utc

    # -- selection (symbol resolution via SymbolResolver, no gateway touch on failure) --

    def _resolve(self, instrument_id: str, timeframe: str) -> str | AdapterFailure:
        """Map ``(instrument_id, timeframe)`` to the provider symbol, or fail."""
        resolution = self._symbol_resolver.resolve(instrument_id, timeframe)
        if isinstance(resolution, SymbolResolutionFailure):
            if resolution.is_timeframe:
                return AdapterFailure(
                    ErrorCode.UNSUPPORTED_TIMEFRAME,
                    "unsupported",
                    (
                        f"timeframe {timeframe!r} is not supported for "
                        f"{instrument_id!r}: {resolution.reason}"
                    ),
                )
            return AdapterFailure(
                ErrorCode.UNSUPPORTED_INSTRUMENT,
                "unsupported",
                f"instrument {instrument_id!r} timeframe {timeframe!r}: {resolution.reason}",
            )
        # Verify the symbol is visible and accessible
        verified = self._symbol_resolver.verify_symbol_access(resolution)
        if isinstance(verified, SymbolResolutionFailure):
            return AdapterFailure(
                ErrorCode.UNSUPPORTED_INSTRUMENT,
                "unsupported",
                f"instrument {instrument_id!r} timeframe {timeframe!r}: {verified.reason}",
            )
        return resolution.provider_symbol

    def _resolve_symbol(self, instrument_id: str) -> str | AdapterFailure:
        """Map an instrument to its symbol for timeframe-free reads (quote/spec).

        Uses H1 as the default timeframe for resolution since symbol
        visibility is timeframe-independent.
        """
        resolution = self._symbol_resolver.resolve(instrument_id, "H1")
        if isinstance(resolution, SymbolResolutionFailure):
            return AdapterFailure(
                ErrorCode.UNSUPPORTED_INSTRUMENT,
                "unsupported",
                f"instrument {instrument_id!r}: {resolution.reason}",
            )
        verified = self._symbol_resolver.verify_symbol_access(resolution)
        if isinstance(verified, SymbolResolutionFailure):
            return AdapterFailure(
                ErrorCode.UNSUPPORTED_INSTRUMENT,
                "unsupported",
                f"instrument {instrument_id!r}: {verified.reason}",
            )
        return resolution.provider_symbol

    # -- session guards ----------------------------------------------------

    def _capture_error(self) -> ProviderKind:
        """Exactly one ``last_error()`` capture, mapped; never leaks payloads."""
        try:
            raw = self._terminal_manager._gateway.last_error()
            code = int(raw[0])
        except Exception:  # noqa: BLE001 — any unreadable error reads disconnected
            return "disconnected"
        return _map_last_error(code)

    def _check_read_only(self) -> AdapterFailure | None:
        """Accept any MT5 session mode (investor/master/demo/live).

        GoldMasters is signals-only: it never places or modifies orders,
        so any MT5 session mode is acceptable for reading market data.
        """
        try:
            terminal = self._terminal_manager._gateway.terminal_info()
            account = self._terminal_manager._gateway.account_info()
        except Exception:  # noqa: BLE001 — any unreadable error reads disconnected
            return _failure_for("disconnected", "mt5 session descriptors are unreadable")
        if terminal is None or not hasattr(terminal, "trade_allowed"):
            return _failure_for(
                "disconnected",
                "terminal descriptor lacks trade_allowed (must-verify-first, RISK-03)",
            )
        if account is None:
            return _failure_for("terminal-closed", "mt5 account is not attached")
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
        """Terminal is already attached by TerminalManager; ``None`` means ready."""
        if not self._terminal_manager.is_ready():
            return _failure_for("terminal-closed", "mt5 terminal manager not started")
        return self._check_read_only()

    def _fetch_rows(
        self, symbol: str, timeframe: str, count: int
    ) -> list[dict[str, Any]] | AdapterFailure:
        """One quick retry (D-51), then disconnected; unsupported never retries."""
        attempts = 1 + max(0, self._retry_attempts)
        failure: AdapterFailure = _failure_for("disconnected", "mt5 read failed")
        for attempt in range(attempts):
            try:
                rows = self._terminal_manager._gateway.copy_rates_from_pos(
                    symbol, timeframe, 0, count + 1
                )
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
            try:
                info = self._terminal_manager._gateway.symbol_info(resolved)
            except Exception:  # noqa: BLE001 — an unreadable descriptor reads disconnected
                return _failure_for("disconnected", "mt5 symbol descriptor unreadable")
            if info is None:
                return _failure_for("unsupported", f"symbol {resolved!r} is not exposed")
            if not getattr(info, "visible", False):
                return _failure_for(
                    "unsupported", f"symbol {resolved!r} is not enabled for reading"
                )
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
            stamped = validate_bars(
                bars,
                now_utc=now,
                stale_closed_bars=self._stale_closed_bars,
                stale_grace_seconds=self._stale_grace_seconds,
                precision_table=precision_table,
                weekend_spec=self._weekend_spec,
                break_spec=self._break_spec,
            )
            return tuple(self._backfill_gaps(stamped, resolved, timeframe, now))
        finally:
            # TerminalManager owns shutdown — do NOT call gateway.shutdown() here
            pass

    def _backfill_gaps(
        self, bars: list[MarketBar], symbol: str, timeframe: str, now: datetime
    ) -> list[MarketBar]:
        """One ``copy_rates_range`` re-fetch per unexpected gap, then re-validate.

        Backfill path only (never the hot path): fills actually-returned closed
        bars into missing spans, never synthesizes. Only hour-opens in the
        missing set are merged — a forming bar or any out-of-span row the
        terminal returns is ignored. First-pass ``MALFORMED``/``DUPLICATE``
        evidence is preserved across the merge; a failed re-fetch keeps the
        ``missing-history`` stamp.
        """
        gaps = _gap_spans(bars)
        if not gaps:
            return bars
        filled: dict[datetime, MarketBar] = {bar.bar_open_time: bar for bar in bars}
        for span_start, span_end, missing in gaps:
            try:
                rows = self._terminal_manager._gateway.copy_rates_range(
                    symbol, timeframe, span_start, span_end
                )
            except Exception:  # noqa: BLE001 — a failed re-fetch keeps missing-history
                continue
            if not rows:
                continue
            try:
                extra = normalize.normalize_bars(
                    sorted(rows, key=lambda row: float(row["time"])),
                    instrument_id=bars[0].instrument_id,
                    provider_symbol=symbol,
                    timeframe=timeframe,
                    server_timezone=self._server_timezone,
                    retrieved_at=now,
                    forming_first=False,
                )
            except (NormalizationError, KeyError, TypeError, ValueError):
                continue
            wanted = set(missing)
            for bar in extra:
                if bar.bar_open_time in wanted and bar.bar_open_time not in filled:
                    filled[bar.bar_open_time] = bar
        merged = [filled[key] for key in sorted(filled)]
        return validate_bars(
            merged,
            now_utc=now,
            stale_closed_bars=self._stale_closed_bars,
            stale_grace_seconds=self._stale_grace_seconds,
            weekend_spec=self._weekend_spec,
            break_spec=self._break_spec,
            preserve={bar.bar_open_time: list(bar.quality_flags) for bar in bars},
        )

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
                    tick = self._terminal_manager._gateway.symbol_info_tick(resolved)
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
            overlap_w, major_w, asia_w = self._session_windows
            limit = quote_stale_limit_for(
                now,
                overlap=overlap,
                major=major,
                asia=asia,
                offhours=self._quote_offhours,
                overlap_windows=overlap_w,
                major_windows=major_w,
                asia_windows=asia_w,
            )
            return validate_quote(
                quote, now_utc=now, stale_seconds=limit, weekend_spec=self._weekend_spec
            )
        finally:
            # TerminalManager owns shutdown — do NOT call gateway.shutdown() here
            pass

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
            try:
                info = self._terminal_manager._gateway.symbol_info(resolved)
            except Exception:  # noqa: BLE001 — an unreadable descriptor reads disconnected
                return _failure_for("disconnected", "mt5 symbol descriptor unreadable")
            if info is None or not getattr(info, "visible", False):
                return _failure_for("unsupported", f"symbol {resolved!r} is not exposed")
            for field in ("digits", "point"):
                if getattr(info, field, None) is None:
                    return _failure_for(
                        "disconnected",
                        f"symbol descriptor lacks {field} (must-verify-first, RISK-03)",
                    )
            try:
                version = self._terminal_manager._gateway.version()
                build = version[1] if version is not None else "unknown"
            except Exception:  # noqa: BLE001 — build provenance degrades, read continues
                build = "unknown"
            # D-3.4: contract size persists as a decimal string; an omitted
            # descriptor field stays None (unknown provenance), never a guess.
            raw_contract_size = getattr(info, "trade_contract_size", None)
            contract_size: str | None = None
            if raw_contract_size is not None:
                try:
                    size = Decimal(str(raw_contract_size))
                except InvalidOperation, ValueError, TypeError:
                    return _failure_for("malformed", "trade_contract_size is not a decimal value")
                if not size.is_finite() or size <= 0:
                    return _failure_for(
                        "malformed", "trade_contract_size must be finite and positive"
                    )
                contract_size = format(size, "f")
            try:
                return PrecisionRow(
                    instrument_id=instrument_id,
                    provider_id=PROVIDER_ID,
                    tick_size=str(info.point),
                    decimals=int(info.digits),
                    contract_size=contract_size,
                    provider_spec_version=f"build {build}",
                    retrieved_at=now,
                    valid_from=now,
                )
            except Exception as exc:  # noqa: BLE001 — contract rejection reads malformed
                return AdapterFailure(ErrorCode.CONFIG_INVALID, "malformed", str(exc))
        finally:
            # TerminalManager owns shutdown — do NOT call gateway.shutdown() here
            pass

    def capabilities(self) -> dict[str, object]:
        """Supported vs unsupported mapping entries for the connected terminal."""
        if not self._terminal_manager.is_ready():
            return {"provider_id": PROVIDER_ID, "supported": [], "unsupported": []}
        try:
            names: set[str] = set()
            try:
                symbols = self._terminal_manager._gateway.symbols_get()
                for entry in symbols or []:
                    name = getattr(entry, "name", None)
                    if isinstance(name, str):
                        names.add(name)
            except Exception:  # noqa: BLE001 — capability probe never raises
                pass
            supported: list[dict[str, object]] = []
            unsupported: list[dict[str, object]] = []
            for canonical_id in CANONICAL_INSTRUMENT_IDS:
                resolution = self._symbol_resolver.resolve(canonical_id, "H1")
                if isinstance(resolution, SymbolResolutionFailure):
                    unsupported.append(
                        {
                            "instrument_id": canonical_id,
                            "provider_symbol": None,
                            "timeframes": ["H1"],
                            "reason": resolution.reason,
                        }
                    )
                    continue
                verified = self._symbol_resolver.verify_symbol_access(resolution)
                if isinstance(verified, SymbolResolutionFailure):
                    unsupported.append(
                        {
                            "instrument_id": canonical_id,
                            "provider_symbol": resolution.provider_symbol,
                            "timeframes": ["H1"],
                            "reason": verified.reason,
                        }
                    )
                    continue
                entry = {
                    "instrument_id": canonical_id,
                    "provider_symbol": resolution.provider_symbol,
                    "timeframes": ["H1"],
                    "confidence": resolution.confidence,
                }
                if resolution.provider_symbol in names:
                    supported.append(entry)
                else:
                    unsupported.append(entry)
            return {"provider_id": PROVIDER_ID, "supported": supported, "unsupported": unsupported}
        finally:
            # TerminalManager owns shutdown — do NOT call gateway.shutdown() here
            pass


def probe_mt5(
    terminal_manager: TerminalManager,
    symbol_resolver: SymbolResolver,
    server_timezone: str,
    bars_count: int,
    weekend_spec: str,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Bounded probe pass; every failure maps to a status, never raises.

    Uses the persistent TerminalManager (already started) rather than
    create/destroy per probe.
    """
    adapter = Mt5Adapter(
        terminal_manager, symbol_resolver, server_timezone=server_timezone, bars_count=bars_count
    )
    now = now_utc or datetime.now(UTC)
    try:
        version = terminal_manager._gateway.version()
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
    weekend = is_weekend_closed(now, weekend_spec)
    if failure_kind is not None and not weekend:
        status = {
            QualityStatus.STALE: "disconnected",
            QualityStatus.MALFORMED: "disconnected",
            QualityStatus.MISSING_HISTORY: "missing-history",
            QualityStatus.UNSUPPORTED: "unsupported-symbol",
            QualityStatus.DISCONNECTED: "disconnected",
        }[failure_kind]
        return _provider_object(
            status,
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