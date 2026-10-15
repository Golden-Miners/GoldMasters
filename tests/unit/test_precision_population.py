"""Precision-table population: spec → append-only row with build provenance.

Proves plan 02-04 Task 1: ``get_instrument_spec`` maps ``digits``/``point``
plus the terminal build string to a ``PrecisionRow``; the caller appends via
``PrecisionTable.with_row`` with ``valid_from=retrieved_at`` and open
``valid_to``; a second fetch supersedes by appending (history intact); audit
lookup at a payload ``retrieved_at`` resolves the row in force (D-26); the
zero-row table still answers unknown (D-19); a malformed spec fails
validation, never a default row.

Known limit (open item for Phase 3): ``PrecisionRow`` carries no
contract-size column and plan 02-04 forbids a contracts change, so
``trade_contract_size`` — observed on the descriptor — is not persisted.
Build + ``retrieved_at`` is the recorded provenance (D-24).
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from goldmasters_contracts import PrecisionRow, PrecisionTable
from pydantic import ValidationError

from services.mt5_adapter.adapter import AdapterFailure, Mt5Adapter

FIXTURE_T1 = datetime(2026, 1, 6, 15, 30, tzinfo=UTC)
FIXTURE_T2 = datetime(2026, 1, 6, 16, 30, tzinfo=UTC)
FIXTURE_VERSION = (500, 4570, "2026-01-01")


def FIXTURE_symbol_info(  # noqa: N802 — fixture prefix is the labelling convention
    moment: datetime, **overrides: Any
) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "digits": 2,
        "point": 0.01,
        "trade_tick_size": 0.01,
        "trade_tick_value": 1.0,
        "trade_contract_size": 100.0,
        "visible": True,
        "time": int(moment.timestamp()),
        "bid": 2387.10,
        "ask": 2387.45,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


class FIXTURE_Terminal:  # noqa: N801 — fixture prefix is the labelling convention
    """Minimal gateway double: only the spec path is exercised here."""

    def __init__(self, info: SimpleNamespace | None) -> None:
        self._info = info

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass

    def version(self) -> tuple[int, int, str]:
        return FIXTURE_VERSION

    def last_error(self) -> tuple[int, str]:
        return (0, "ok")

    def symbol_info(self, symbol: str) -> SimpleNamespace | None:
        assert symbol == "XAUUSD"
        return self._info

    def terminal_info(self) -> SimpleNamespace:
        return SimpleNamespace(trade_allowed=False)

    def account_info(self) -> SimpleNamespace:
        return SimpleNamespace(balance=10000.0, currency="USD")


def _spec(info: SimpleNamespace | None, now: datetime) -> PrecisionRow | AdapterFailure:
    adapter = Mt5Adapter(
        FIXTURE_Terminal(info), server_timezone="UTC", retry_delay_ms=1  # type: ignore[arg-type]
    )
    return adapter.get_instrument_spec("xauusd", now_utc=now)


def test_spec_maps_digits_point_build_to_row() -> None:
    result = _spec(FIXTURE_symbol_info(FIXTURE_T1), FIXTURE_T1)
    assert not isinstance(result, AdapterFailure)
    assert result.instrument_id == "xauusd"
    assert result.provider_id == "mt5"
    assert result.decimals == 2  # digits → decimals
    assert result.tick_size == "0.01"  # point → tick_size string
    assert result.provider_spec_version == "build 4570"  # version() build
    assert result.retrieved_at == FIXTURE_T1
    assert result.valid_from == FIXTURE_T1  # valid_from = retrieved_at
    assert result.valid_to is None  # open interval


def test_second_fetch_supersedes_by_appending_history_intact() -> None:
    first = _spec(FIXTURE_symbol_info(FIXTURE_T1), FIXTURE_T1)
    second = _spec(FIXTURE_symbol_info(FIXTURE_T2), FIXTURE_T2)
    assert not isinstance(first, AdapterFailure)
    assert not isinstance(second, AdapterFailure)
    table = PrecisionTable().with_row(first).with_row(second)
    assert len(table.rows) == 2  # append-only: both rows present
    assert table.rows[0].retrieved_at == FIXTURE_T1
    assert table.rows[1].retrieved_at == FIXTURE_T2


def test_audit_lookup_resolves_row_in_force_at_retrieved_at() -> None:
    first = _spec(FIXTURE_symbol_info(FIXTURE_T1), FIXTURE_T1)
    second = _spec(FIXTURE_symbol_info(FIXTURE_T2), FIXTURE_T2)
    assert not isinstance(first, AdapterFailure)
    assert not isinstance(second, AdapterFailure)
    table = PrecisionTable().with_row(first).with_row(second)
    between = datetime(2026, 1, 6, 16, 0, tzinfo=UTC)
    found = table.lookup("xauusd", "mt5", at=between)
    assert found.status == "found"
    assert found.row is not None
    assert found.row.retrieved_at == FIXTURE_T1  # D-26 interval resolution


def test_zero_row_table_lookup_answers_unknown() -> None:
    assert PrecisionTable().lookup("xauusd", "mt5").status == "unknown"
    assert PrecisionTable().lookup("xauusd", "mt5", at=FIXTURE_T1).status == "unknown"
    assert PrecisionTable().lookup("silver", "mt5", at=FIXTURE_T1).status == "unknown"


def test_malformed_spec_fails_validation_never_a_default_row() -> None:
    with pytest.raises(ValidationError):
        PrecisionRow(
            instrument_id="xauusd",
            provider_id="mt5",
            tick_size="0.01",
            decimals=-1,  # ge=0 rejects
            provider_spec_version="build 4570",
            retrieved_at=FIXTURE_T1,
            valid_from=FIXTURE_T1,
        )
    bad = _spec(FIXTURE_symbol_info(FIXTURE_T1, digits="bad"), FIXTURE_T1)
    assert isinstance(bad, AdapterFailure)  # never a default row
    assert bad.kind == "malformed"
    assert bad.code.retryable is False
