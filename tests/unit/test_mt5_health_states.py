"""Provider health-state tests (02-03 Task 1: D-50, criterion 6; research §1/§5).

A locally configurable gateway double forces every terminal failure; each
must land in exactly one of {connected, terminal-closed, disconnected,
missing-history, unsupported-symbol} per the tracer precedence. Labelled
fixtures (``FIXTURE_`` prefix, tests-only) — never live data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from goldmasters_contracts import ErrorCode

from services.mt5_adapter.adapter import AdapterFailure, Mt5Adapter, probe_mt5
from services.mt5_adapter.symbol_resolver import SymbolResolver
from services.mt5_adapter.terminal import TerminalManager

#: Tuesday 2026-01-06 — mid-week, far from any closed window.
FIXTURE_TUESDAY = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
FIXTURE_SATURDAY = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)

WEEKEND_SPEC = "Fri 21:00-Sun 22:00"


def FIXTURE_row(open_time: datetime) -> dict[str, Any]:  # noqa: N802
    return {
        "time": int(open_time.timestamp()),
        "open": 2381.0,
        "high": 2383.0,
        "low": 2380.0,
        "close": 2382.0,
        "tick_volume": 100,
        "spread": 35,
        "real_volume": 0,
    }


def FIXTURE_closed_rows(  # noqa: N802
    first: datetime, count: int, *, skip: set[int] | None = None
) -> list[dict[str, Any]]:
    """Terminal order (forming first) over consecutive H1 opens from ``first``."""
    skip = skip or set()
    closed = [FIXTURE_row(first + timedelta(hours=i)) for i in range(count) if i not in skip]
    forming = FIXTURE_row(first + timedelta(hours=count))
    return [forming, *reversed(closed)]


def FIXTURE_info(moment: datetime, *, visible: bool = True) -> SimpleNamespace:  # noqa: N802
    return SimpleNamespace(
        digits=2,
        point=0.01,
        trade_tick_size=0.01,
        trade_tick_value=1.0,
        trade_contract_size=100.0,
        visible=visible,
        time=int(moment.timestamp()),
        bid=2387.10,
        ask=2387.45,
    )


class FIXTURE_terminal:  # noqa: N801 - fixture prefix is the labelling convention
    """Counting gateway double; ``raise_on`` names methods that raise."""

    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        tick: dict[str, Any] | None = None,
        info: SimpleNamespace | None = None,
        initialize: bool = True,
        error: tuple[int, str] = (0, "ok"),
        trade_allowed: bool = False,
        raise_on: set[str] | None = None,
    ) -> None:
        self._rows = rows
        self._tick = tick
        self._info = info
        self._initialize = initialize
        self._error = error
        self._trade_allowed = trade_allowed
        self._raise_on = raise_on or set()
        self.calls: list[str] = []

    def _maybe_raise(self, name: str) -> None:
        self.calls.append(name)
        if name in self._raise_on:
            raise RuntimeError(f"terminal blew up in {name}")

    def initialize(self) -> bool:
        self._maybe_raise("initialize")
        return self._initialize

    def shutdown(self) -> None:
        self.calls.append("shutdown")

    def version(self) -> tuple[int, int, str]:
        self._maybe_raise("version")
        return (500, 4570, "2026-01-01")

    def last_error(self) -> tuple[int, str]:
        self.calls.append("last_error")
        return self._error

    def copy_rates_from_pos(
        self, symbol: str, timeframe: str, start_pos: int, count: int
    ) -> list[dict[str, Any]] | None:
        self._maybe_raise(f"copy_rates_from_pos:{symbol}")
        return self._rows

    def copy_rates_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]] | None:
        self._maybe_raise("copy_rates_range")
        return None

    def symbol_info_tick(self, symbol: str) -> dict[str, Any] | None:
        self._maybe_raise(f"symbol_info_tick:{symbol}")
        return self._tick

    def symbol_info(self, symbol: str) -> SimpleNamespace | None:
        self._maybe_raise(f"symbol_info:{symbol}")
        return self._info

    def symbols_get(self) -> list[SimpleNamespace]:
        self._maybe_raise("symbols_get")
        return [SimpleNamespace(name="XAUUSD")]

    def terminal_info(self) -> SimpleNamespace:
        self._maybe_raise("terminal_info")
        return SimpleNamespace(trade_allowed=self._trade_allowed)

    def account_info(self) -> SimpleNamespace:
        self._maybe_raise("account_info")
        return SimpleNamespace(balance=10000.0, currency="USD")


def _adapter(terminal: FIXTURE_terminal) -> Mt5Adapter:
    tm = TerminalManager(terminal)
    tm._initialized = True  # Bypass terminal start for tests
    resolver = SymbolResolver(terminal)
    return Mt5Adapter(
        tm,
        resolver,
        server_timezone="UTC",
        retry_delay_ms=1,
        weekend_close_utc=WEEKEND_SPEC,
    )


def _fresh_terminal(now: datetime) -> FIXTURE_terminal:
    hour = now.replace(minute=0, second=0, microsecond=0)
    return FIXTURE_terminal(
        rows=FIXTURE_closed_rows(hour - timedelta(hours=10), 10),
        info=FIXTURE_info(now),
    )


def _probe(terminal: FIXTURE_terminal, now: datetime) -> dict[str, object]:
    tm = TerminalManager(terminal)
    tm.start()  # Calls gateway.initialize(); respects terminal._initialize
    resolver = SymbolResolver(terminal)
    return probe_mt5(
        tm,
        resolver,
        server_timezone="UTC",
        bars_count=10,
        now_utc=now,
        weekend_spec=WEEKEND_SPEC,
    )


def test_initialize_false_forces_terminal_closed() -> None:
    terminal = _fresh_terminal(FIXTURE_TUESDAY)
    terminal._initialize = False
    tm = TerminalManager(terminal)
    # Don't call start() - let initialize() fail naturally
    resolver = SymbolResolver(terminal)
    adapter = Mt5Adapter(tm, resolver, server_timezone="UTC", retry_delay_ms=1, weekend_close_utc=WEEKEND_SPEC)
    result = adapter.get_bars("xauusd", "H1", now_utc=FIXTURE_TUESDAY)
    assert isinstance(result, AdapterFailure)
    assert result.kind == "terminal-closed"
    assert _probe(terminal, FIXTURE_TUESDAY)["status"] == "terminal-closed"


def test_mid_session_none_reads_disconnected_after_single_retry() -> None:
    for code in (-1, -3, -10005):
        terminal = FIXTURE_terminal(
            rows=None,
            info=FIXTURE_info(FIXTURE_TUESDAY),
            error=(code, "boom"),
        )
        result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_TUESDAY)
        assert isinstance(result, AdapterFailure)
        assert result.kind == "disconnected", code
        attempts = [c for c in terminal.calls if c.startswith("copy_rates_from_pos")]
        assert len(attempts) == 2, code  # exactly one retry (D-51)


def test_symbol_not_visible_is_unsupported_with_no_fallback() -> None:
    terminal = _fresh_terminal(FIXTURE_TUESDAY)
    terminal._info = FIXTURE_info(FIXTURE_TUESDAY, visible=False)
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_TUESDAY)
    assert isinstance(result, AdapterFailure)
    assert result.kind == "unsupported"
    assert result.code == ErrorCode.UNSUPPORTED_INSTRUMENT
    # symbols_get is called once for symbol resolution; copy_rates_range is
    # never called because the symbol is rejected before bar fetch.
    assert any(c == "symbols_get" for c in terminal.calls)
    assert not any(c.startswith("copy_rates_range") for c in terminal.calls)


def test_midweek_gap_reads_missing_history() -> None:
    rows = FIXTURE_closed_rows(FIXTURE_TUESDAY - timedelta(hours=10), 10, skip={4, 5})
    terminal = FIXTURE_terminal(rows=rows, info=FIXTURE_info(FIXTURE_TUESDAY))
    assert _probe(terminal, FIXTURE_TUESDAY)["status"] == "missing-history"


def test_stale_batch_degrades_health() -> None:
    """Five-hour-old bars: stale quality, provider degraded (never fresh)."""
    old = FIXTURE_TUESDAY - timedelta(hours=5)
    terminal = FIXTURE_terminal(
        rows=FIXTURE_closed_rows(old - timedelta(hours=10), 10),
        info=FIXTURE_info(FIXTURE_TUESDAY),
    )
    body = _probe(terminal, FIXTURE_TUESDAY)
    assert body["status"] == "disconnected"
    assert body["market_open"] is True


def test_logged_out_reads_terminal_closed_never_healthy() -> None:
    terminal = FIXTURE_terminal(
        rows=None,
        info=FIXTURE_info(FIXTURE_TUESDAY),
        error=(-6, "not authorized"),
    )
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_TUESDAY)
    assert isinstance(result, AdapterFailure)
    assert result.kind == "terminal-closed"
    assert _probe(terminal, FIXTURE_TUESDAY)["status"] == "terminal-closed"


def test_probe_never_raises_and_leaks_nothing() -> None:
    terminal = FIXTURE_terminal(
        rows=None,
        info=None,
        error=(-1, "login alpha on //srv/secret failed"),
        raise_on={"symbol_info", "symbol_info_tick", "version"},
    )
    body = _probe(terminal, FIXTURE_TUESDAY)
    assert set(body) == {
        "provider_id",
        "status",
        "market_open",
        "terminal_build",
        "last_bar_close_time",
        "last_quote_time",
        "checked_at",
    }
    assert "alpha" not in str(body) and "srv" not in str(body) and "login" not in str(body)


def test_fresh_weekend_probe_is_connected_market_closed() -> None:
    body = _probe(_fresh_terminal(FIXTURE_SATURDAY), FIXTURE_SATURDAY)
    assert body["status"] == "connected"
    assert body["market_open"] is False
