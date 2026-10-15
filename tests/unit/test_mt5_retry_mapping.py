"""Single-retry rule + last_error mapping + redaction tests (02-03 Task 2: D-51).

A counting gateway double proves exact attempt counts, single-capture counts,
the full research §1 code table, and that terminal text never reaches API
bodies. Labelled fixtures (``FIXTURE_`` prefix, tests-only) — never live data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from services.mt5_adapter.adapter import AdapterFailure, Mt5Adapter, _map_last_error

#: Tuesday 2026-01-06 — mid-week, far from any closed window.
FIXTURE_TUESDAY = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)


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


def FIXTURE_info(moment: datetime) -> SimpleNamespace:  # noqa: N802
    return SimpleNamespace(
        digits=2,
        point=0.01,
        trade_tick_size=0.01,
        trade_tick_value=1.0,
        trade_contract_size=100.0,
        visible=True,
        time=int(moment.timestamp()),
        bid=2387.10,
        ask=2387.45,
    )


class FIXTURE_flaky_terminal:  # noqa: N801 - fixture prefix is the labelling convention
    """Fails ``fail_times`` reads with ``error``, then serves ``rows``."""

    def __init__(
        self,
        *,
        rows: list[dict[str, Any]],
        fail_times: int,
        error: tuple[int, str],
        info: SimpleNamespace,
    ) -> None:
        self._rows = rows
        self._fail_times = fail_times
        self._error = error
        self._info = info
        self.reads = 0
        self.captures = 0

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass

    def version(self) -> tuple[int, int, str]:
        return (500, 4570, "2026-01-01")

    def last_error(self) -> tuple[int, str]:
        self.captures += 1
        return self._error

    def copy_rates_from_pos(
        self, symbol: str, timeframe: str, start_pos: int, count: int
    ) -> list[dict[str, Any]] | None:
        self.reads += 1
        if self.reads <= self._fail_times:
            return None
        return self._rows

    def copy_rates_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]] | None:
        return None

    def symbol_info(self, symbol: str) -> SimpleNamespace | None:
        return self._info

    def symbol_info_tick(self, symbol: str) -> dict[str, Any] | None:
        return None

    def symbols_get(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(name="XAUUSD")]

    def terminal_info(self) -> SimpleNamespace:
        return SimpleNamespace(trade_allowed=False)

    def account_info(self) -> SimpleNamespace:
        return SimpleNamespace(balance=10000.0, currency="USD")


def _rows(first: datetime, count: int) -> list[dict[str, Any]]:
    from datetime import timedelta

    closed = [FIXTURE_row(first + timedelta(hours=i)) for i in range(count)]
    return [FIXTURE_row(first + timedelta(hours=count)), *reversed(closed)]


def _adapter(terminal: FIXTURE_flaky_terminal) -> Mt5Adapter:
    return Mt5Adapter(terminal, server_timezone="UTC", retry_delay_ms=1)


def test_transient_failure_retried_exactly_once() -> None:
    terminal = FIXTURE_flaky_terminal(
        rows=_rows(datetime(2026, 1, 6, 2, 0, tzinfo=UTC), 10),
        fail_times=99,
        error=(-1, "RES_E_FAIL"),
        info=FIXTURE_info(FIXTURE_TUESDAY),
    )
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_TUESDAY)
    assert isinstance(result, AdapterFailure)
    assert result.kind == "disconnected"
    assert terminal.reads == 2  # one retry, then stop (D-51)
    assert terminal.captures == 2  # exactly one capture per failed read


def test_non_retryable_codes_never_retry() -> None:
    expectations = {
        -2: "unsupported",  # RES_E_INVALID_PARAMS
        -7: "unsupported",  # RES_E_UNSUPPORTED
        -4: "missing-history",  # RES_E_NOT_FOUND
    }
    for code, kind in expectations.items():
        terminal = FIXTURE_flaky_terminal(
            rows=_rows(datetime(2026, 1, 6, 2, 0, tzinfo=UTC), 10),
            fail_times=99,
            error=(code, "nope"),
            info=FIXTURE_info(FIXTURE_TUESDAY),
        )
        result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_TUESDAY)
        assert isinstance(result, AdapterFailure)
        assert result.kind == kind, code
        assert terminal.reads == 1, code  # no retry for non-retryable codes


def test_recovery_on_retry_returns_data() -> None:
    terminal = FIXTURE_flaky_terminal(
        rows=_rows(datetime(2026, 1, 6, 2, 0, tzinfo=UTC), 10),
        fail_times=1,
        error=(-1, "RES_E_FAIL"),
        info=FIXTURE_info(FIXTURE_TUESDAY),
    )
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_TUESDAY)
    assert not isinstance(result, AdapterFailure)
    assert len(result) == 10
    assert terminal.reads == 2


def test_full_code_table_maps_per_research() -> None:
    assert _map_last_error(1) == "disconnected"  # RES_S_OK with None payload: no success signal
    assert _map_last_error(-1) == "disconnected"  # RES_E_FAIL
    assert _map_last_error(-2) == "unsupported"  # RES_E_INVALID_PARAMS
    assert _map_last_error(-3) == "disconnected"  # RES_E_NO_MEMORY (retryable once)
    assert _map_last_error(-4) == "missing-history"  # RES_E_NOT_FOUND
    assert _map_last_error(-6) == "terminal-closed"  # RES_E_AUTH_FAILED
    assert _map_last_error(-7) == "unsupported"  # RES_E_UNSUPPORTED
    assert _map_last_error(-8) == "disconnected"  # RES_E_AUTO_TRADING_DISABLED
    assert _map_last_error(-10005) == "disconnected"  # TIMEOUT
    assert _map_last_error(-10000) == "disconnected"  # internal range


def test_terminal_text_reaches_no_api_body() -> None:
    leak = "login alpha on //srv/secret/XAUUSD"
    terminal = FIXTURE_flaky_terminal(
        rows=_rows(datetime(2026, 1, 6, 2, 0, tzinfo=UTC), 10),
        fail_times=99,
        error=(-1, leak),
        info=FIXTURE_info(FIXTURE_TUESDAY),
    )
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_TUESDAY)
    assert isinstance(result, AdapterFailure)
    assert "alpha" not in result.message
    assert "srv" not in result.message
