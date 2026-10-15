"""MT5 tracer tests: FakeTerminal through gateway → adapter → normalize → validation.

Every row below is a labelled fixture (``FIXTURE_`` prefix, tests-only) —
never live data. A repo-grep test in ``test_mt5_health_api.py`` proves no
``FIXTURE_`` symbol is importable from production paths.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from goldmasters_contracts import (
    ErrorCode,
    PrecisionRow,
    PrecisionTable,
    QualityStatus,
    VolumeType,
)

from services.mt5_adapter.adapter import AdapterFailure, Mt5Adapter
from services.mt5_adapter.validation import quote_stale_limit_for

# -- labelled fixtures (tests-only, never live) -----------------------------

#: Tuesday 2026-01-06 10:00 UTC: mid-week, far from any weekend window.
FIXTURE_T0 = datetime(2026, 1, 6, 10, 0, tzinfo=UTC)
FIXTURE_NOW_FRESH = datetime(2026, 1, 6, 15, 30, tzinfo=UTC)

FIXTURE_VERSION = (500, 4570, "2026-01-01")


def _epoch(moment: datetime, wall_offset_seconds: int = 0) -> int:
    """Server-wall epoch for a true instant under a fixed zone offset."""
    return int(moment.timestamp()) + wall_offset_seconds


def FIXTURE_bar_row(  # noqa: N802 — fixture prefix is the labelling convention
    open_time: datetime,
    o: float,
    h: float,
    lo: float,
    c: float,
    tick_volume: int = 100,
    wall_offset_seconds: int = 0,
) -> dict[str, Any]:
    return {
        "time": _epoch(open_time, wall_offset_seconds),
        "open": o,
        "high": h,
        "low": lo,
        "close": c,
        "tick_volume": tick_volume,
        "spread": 35,
        "real_volume": 0,
    }


def FIXTURE_closed_rows(  # noqa: N802
    wall_offset_seconds: int = 0, zero_volume_index: int | None = None
) -> list[dict[str, Any]]:
    """Six rows in terminal order: the pos-0 forming bar first, then closed H1 bars."""
    chronological = [
        (10, 2380.00, 2382.50, 2379.00, 2381.00, 100),
        (11, 2381.00, 2384.00, 2380.50, 2383.00, 101),
        (12, 2383.00, 2385.50, 2382.00, 2384.00, 102),
        (13, 2384.00, 2386.00, 2383.50, 2385.00, 103),
        (14, 2385.00, 2387.50, 2384.00, 2386.50, 104),
    ]
    rows = [
        FIXTURE_bar_row(
            datetime(2026, 1, 6, hour, tzinfo=UTC),
            o,
            h,
            lo,
            c,
            tick_volume=0 if index == zero_volume_index else volume,
            wall_offset_seconds=wall_offset_seconds,
        )
        for index, (hour, o, h, lo, c, volume) in enumerate(chronological)
    ]
    forming = FIXTURE_bar_row(
        datetime(2026, 1, 6, 15, tzinfo=UTC),
        2386.50,
        2388.00,
        2385.50,
        2387.00,
        tick_volume=140,
        wall_offset_seconds=wall_offset_seconds,
    )
    return [forming, *reversed(rows)]


def FIXTURE_tick(  # noqa: N802
    moment: datetime, *, last: float = 2387.05, wall_offset_seconds: int = 0
) -> dict[str, Any]:
    ms = _epoch(moment, wall_offset_seconds) * 1000
    return {
        "time": _epoch(moment, wall_offset_seconds),
        "bid": 2387.10,
        "ask": 2387.45,
        "last": last,
        "volume": 0,
        "time_msc": ms,
        "flags": 0,
        "volume_real": 0.0,
    }


def FIXTURE_symbol_info(  # noqa: N802
    moment: datetime, *, visible: bool = True, wall_offset_seconds: int = 0
) -> SimpleNamespace:
    return SimpleNamespace(
        digits=2,
        point=0.01,
        trade_tick_size=0.01,
        trade_tick_value=1.0,
        trade_contract_size=100.0,
        visible=visible,
        time=_epoch(moment, wall_offset_seconds),
        bid=2387.10,
        ask=2387.45,
    )


class FakeTerminal:
    """Gateway double recording every call (proves no-fallback assertions)."""

    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        tick: dict[str, Any] | None = None,
        info: SimpleNamespace | None = None,
        initialize: bool = True,
        error: tuple[int, str] = (0, "ok"),
        trade_allowed: bool = False,
        names: list[str] | None = None,
    ) -> None:
        self._rows = rows
        self._tick = tick
        self._info = info
        self._initialize = initialize
        self._error = error
        self._trade_allowed = trade_allowed
        self._names = ["XAUUSD"] if names is None else names
        self.calls: list[str] = []

    def initialize(self) -> bool:
        self.calls.append("initialize")
        return self._initialize

    def shutdown(self) -> None:
        self.calls.append("shutdown")

    def version(self) -> tuple[int, int, str]:
        self.calls.append("version")
        return FIXTURE_VERSION

    def last_error(self) -> tuple[int, str]:
        self.calls.append("last_error")
        return self._error

    def copy_rates_from_pos(
        self, symbol: str, timeframe: str, start_pos: int, count: int
    ) -> list[dict[str, Any]] | None:
        self.calls.append(f"copy_rates_from_pos:{symbol}:{timeframe}:{start_pos}:{count}")
        return self._rows

    def copy_rates_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]] | None:
        self.calls.append("copy_rates_range")
        return self._rows

    def symbol_info(self, symbol: str) -> SimpleNamespace | None:
        self.calls.append(f"symbol_info:{symbol}")
        return self._info

    def symbol_info_tick(self, symbol: str) -> dict[str, Any] | None:
        self.calls.append(f"symbol_info_tick:{symbol}")
        return self._tick

    def symbols_get(self) -> list[SimpleNamespace]:
        self.calls.append("symbols_get")
        return [SimpleNamespace(name=name) for name in self._names]

    def terminal_info(self) -> SimpleNamespace:
        self.calls.append("terminal_info")
        return SimpleNamespace(trade_allowed=self._trade_allowed)

    def account_info(self) -> SimpleNamespace:
        self.calls.append("account_info")
        return SimpleNamespace(balance=10000.0, currency="USD")


def _adapter(terminal: FakeTerminal, **overrides: Any) -> Mt5Adapter:
    params: dict[str, Any] = {"server_timezone": "UTC", "retry_delay_ms": 1}
    params.update(overrides)
    return Mt5Adapter(terminal, **params)


def _fresh_terminal(**overrides: Any) -> FakeTerminal:
    rows = FIXTURE_closed_rows()
    now = FIXTURE_NOW_FRESH
    args: dict[str, Any] = {
        "rows": rows,
        "tick": FIXTURE_tick(now),
        "info": FIXTURE_symbol_info(now),
    }
    args.update(overrides)
    return FakeTerminal(**args)


# -- tracer behaviors ---------------------------------------------------------


def test_tracer_bars_flow_end_to_end() -> None:
    terminal = _fresh_terminal()
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert not isinstance(result, AdapterFailure)
    assert len(result) == 5  # pos-0 forming bar dropped
    first = result[0]
    assert first.instrument_id == "xauusd"
    assert first.provider_id == "mt5"
    assert first.provider_symbol == "XAUUSD"
    assert first.timeframe == "H1"
    assert first.bar_open_time == FIXTURE_T0
    assert first.quality_status == QualityStatus.OK
    assert first.quality_flags == []
    assert first.volume_type == VolumeType.TICK
    assert first.volume == Decimal(100)
    assert first.retrieved_at == FIXTURE_NOW_FRESH
    assert first.source_timezone == "UTC"
    assert [b.bar_open_time.hour for b in result] == [10, 11, 12, 13, 14]


def test_zero_volume_row_maps_to_not_available() -> None:
    terminal = _fresh_terminal(rows=FIXTURE_closed_rows(zero_volume_index=2))
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert not isinstance(result, AdapterFailure)
    assert result[1].volume == Decimal(101)
    assert result[1].volume_type == VolumeType.TICK
    assert result[2].volume is None
    assert result[2].volume_type == VolumeType.NOT_AVAILABLE


def test_server_timezone_converts_wall_to_utc() -> None:
    offset = 2 * 3600  # Europe/Athens in January: UTC+2, no DST edge
    now_wall = _epoch(FIXTURE_NOW_FRESH, offset)
    terminal = FakeTerminal(
        rows=FIXTURE_closed_rows(wall_offset_seconds=offset),
        tick=FIXTURE_tick(FIXTURE_NOW_FRESH, wall_offset_seconds=offset),
        info=FIXTURE_symbol_info(FIXTURE_NOW_FRESH, wall_offset_seconds=offset),
    )
    adapter = _adapter(terminal, server_timezone="Europe/Athens")
    result = adapter.get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert not isinstance(result, AdapterFailure)
    assert result[0].bar_open_time == FIXTURE_T0
    assert result[0].source_timezone == "Europe/Athens"
    assert now_wall - int(FIXTURE_NOW_FRESH.timestamp()) == offset


def test_clock_skew_against_zone_fails_disconnected() -> None:
    terminal = _fresh_terminal()  # UTC walls...
    adapter = _adapter(terminal, server_timezone="Europe/Athens")  # ...against +2h zone
    result = adapter.get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert isinstance(result, AdapterFailure)
    assert result.code == ErrorCode.INTERNAL_ERROR
    assert result.kind == "disconnected"


def test_quote_spread_and_zero_last() -> None:
    terminal = _fresh_terminal(tick=FIXTURE_tick(FIXTURE_NOW_FRESH, last=0.0))
    result = _adapter(terminal).get_latest_quote("xauusd", now_utc=FIXTURE_NOW_FRESH)
    assert not isinstance(result, AdapterFailure)
    assert result.bid == Decimal("2387.10")
    assert result.ask == Decimal("2387.45")
    assert result.spread == result.ask - result.bid == Decimal("0.35")
    assert result.last is None  # last=0.0 is normal for XAUUSD: mapped, never priced
    assert result.last_time is None
    assert result.quality_status == QualityStatus.OK


def test_spec_row_carries_build_provenance() -> None:
    terminal = _fresh_terminal()
    result = _adapter(terminal).get_instrument_spec("xauusd", now_utc=FIXTURE_NOW_FRESH)
    assert not isinstance(result, AdapterFailure)
    assert result.tick_size == "0.01"
    assert result.decimals == 2
    assert result.provider_spec_version == "build 4570"
    assert result.valid_from == FIXTURE_NOW_FRESH
    table = PrecisionTable().with_row(result)
    assert table.lookup("xauusd", "mt5").status == "found"
    assert PrecisionTable().lookup("xauusd", "mt5").status == "unknown"


def test_unsupported_selection_makes_no_gateway_call() -> None:
    terminal = _fresh_terminal()
    adapter = _adapter(terminal)
    bad_instrument = adapter.get_bars("silver", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert isinstance(bad_instrument, AdapterFailure)
    assert bad_instrument.code == ErrorCode.UNSUPPORTED_INSTRUMENT
    assert bad_instrument.code.value == "UNSUPPORTED_INSTRUMENT"  # typo locked, errors.py:30
    bad_timeframe = adapter.get_bars("xauusd", "M5", now_utc=FIXTURE_NOW_FRESH)
    assert isinstance(bad_timeframe, AdapterFailure)
    assert bad_timeframe.code == ErrorCode.UNSUPPORTED_TIMEFRAME
    assert terminal.calls == []


def test_transient_failure_retries_once_then_disconnects() -> None:
    now = FIXTURE_NOW_FRESH
    terminal = FakeTerminal(
        rows=None,
        error=(-1, "generic fail"),
        tick=None,
        info=FIXTURE_symbol_info(now),
    )
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=now)
    assert isinstance(result, AdapterFailure)
    assert result.code == ErrorCode.INTERNAL_ERROR
    assert result.code.retryable is True
    copies = [c for c in terminal.calls if c.startswith("copy_rates_from_pos")]
    assert len(copies) == 2  # D-51: one quick retry, then disconnected
    assert terminal.calls.count("last_error") == 2  # exactly one capture per None


def test_missing_history_never_retries() -> None:
    terminal = FakeTerminal(
        rows=None, error=(-4, "no history"), info=FIXTURE_symbol_info(FIXTURE_NOW_FRESH)
    )
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert isinstance(result, AdapterFailure)
    assert result.kind == "missing-history"
    assert result.code.retryable is False
    copies = [c for c in terminal.calls if c.startswith("copy_rates_from_pos")]
    assert len(copies) == 1


def test_terminal_closed_maps_visibly() -> None:
    terminal = FakeTerminal(initialize=False, error=(-6, "auth failed"))
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert isinstance(result, AdapterFailure)
    assert result.kind == "terminal-closed"
    assert "copy_rates_from_pos" not in " ".join(terminal.calls)


def test_master_session_is_refused() -> None:
    terminal = _fresh_terminal(trade_allowed=True)
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert isinstance(result, AdapterFailure)
    assert result.kind == "terminal-closed"


def test_hidden_symbol_is_unsupported() -> None:
    terminal = _fresh_terminal(info=FIXTURE_symbol_info(FIXTURE_NOW_FRESH, visible=False))
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert isinstance(result, AdapterFailure)
    assert result.code == ErrorCode.UNSUPPORTED_INSTRUMENT


def test_stale_batch_is_never_healthy() -> None:
    stale_now = datetime(2026, 1, 6, 18, 0, tzinfo=UTC)  # last close 15:00 + 3h
    terminal = FakeTerminal(
        rows=FIXTURE_closed_rows(),
        tick=FIXTURE_tick(stale_now),
        info=FIXTURE_symbol_info(stale_now),
    )
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=stale_now)
    assert not isinstance(result, AdapterFailure)
    assert all(b.quality_status == QualityStatus.STALE for b in result)


def test_gap_and_duplicate_flagged_not_dropped_silently() -> None:
    rows = FIXTURE_closed_rows()  # terminal order: [forming, 14, 13, 12, 11, 10]
    gapped = [rows[0], rows[1], rows[3], rows[4], rows[5]]  # 13:00 missing
    terminal = _fresh_terminal(rows=[*gapped[:3], rows[3], *gapped[3:]])  # 12:00 twice
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert not isinstance(result, AdapterFailure)
    assert len(result) == 4  # duplicate dropped, first kept and flagged
    by_hour = {b.bar_open_time.hour: b for b in result}
    assert QualityStatus.DUPLICATE in by_hour[12].quality_flags
    assert QualityStatus.GAP in by_hour[14].quality_flags
    assert by_hour[14].quality_status == QualityStatus.GAP


def test_out_of_order_bar_is_malformed() -> None:
    rows = FIXTURE_closed_rows()
    rows[2], rows[3] = rows[3], rows[2]  # swap the 13:00 and 12:00 closed bars
    terminal = _fresh_terminal(rows=rows)
    result = _adapter(terminal).get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert not isinstance(result, AdapterFailure)
    assert any(b.quality_status == QualityStatus.MALFORMED for b in result)


def test_tick_align_applies_only_with_precision_row() -> None:
    terminal = _fresh_terminal()
    adapter = _adapter(terminal)
    rows = adapter.get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH)
    assert not isinstance(rows, AdapterFailure)
    assert all(b.quality_status == QualityStatus.OK for b in rows)
    aligned = PrecisionRow(
        instrument_id="xauusd",
        provider_id="mt5",
        tick_size="0.50",
        decimals=2,
        provider_spec_version="build 4570",
        retrieved_at=FIXTURE_NOW_FRESH,
        valid_from=FIXTURE_NOW_FRESH,
    )
    table = PrecisionTable().with_row(aligned)
    checked = adapter.get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH, precision_table=table)
    assert not isinstance(checked, AdapterFailure)
    # 2381.00 % 0.50 == 0 but 2383.00... all end in .00/.50 here except none:
    # 2386.50 % 0.50 == 0 — every close aligns, so the batch stays healthy.
    assert all(b.quality_status == QualityStatus.OK for b in checked)
    misaligned = aligned.model_copy(update={"tick_size": "0.30"})
    bad_table = PrecisionTable().with_row(misaligned)
    flagged = adapter.get_bars("xauusd", "H1", now_utc=FIXTURE_NOW_FRESH, precision_table=bad_table)
    assert not isinstance(flagged, AdapterFailure)
    assert any(b.quality_status == QualityStatus.MALFORMED for b in flagged)


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [(14, 0, 30), (9, 0, 60), (20, 0, 60), (4, 0, 180), (22, 0, 300)],
)
def test_quote_session_limits(hour: int, minute: int, expected: int) -> None:
    moment = datetime(2026, 1, 6, hour, minute, tzinfo=UTC)
    assert quote_stale_limit_for(moment, overlap=30, major=60, asia=180, offhours=300) == expected


def test_capabilities_reports_without_substituting() -> None:
    terminal = _fresh_terminal()
    report = _adapter(terminal).capabilities()
    assert report["provider_id"] == "mt5"
    assert report["supported"] == [
        {"instrument_id": "xauusd", "provider_symbol": "XAUUSD", "timeframes": ["H1"]}
    ]
    assert report["unsupported"] == []
    missing = _fresh_terminal(names=[])
    empty = _adapter(missing).capabilities()
    assert empty["supported"] == []
    assert isinstance(empty["unsupported"], list)
    assert len(empty["unsupported"]) == 1  # reported, never auto-substituted
