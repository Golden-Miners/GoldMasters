"""MT5 market contract tests: adapter outputs × conformance mutations.

Success side: every adapter success output (bars across quality paths,
quote, spec) constructs ``MarketBar``/``MarketQuote``/``PrecisionRow`` and
round-trips through wire JSON. Rejection side: every mutation (wrong enum,
missing field, null-where-not-nullable, NaN/Inf, float price, unknown extra)
still fails construction — the contract gate (D-04) holds over adapter data.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from goldmasters_contracts import MarketBar, MarketQuote, PrecisionRow
from pydantic import ValidationError

from services.mt5_adapter.adapter import AdapterFailure, Mt5Adapter

FIXTURE_NOW = datetime(2026, 1, 6, 15, 30, tzinfo=UTC)
FIXTURE_VERSION = (500, 4570, "2026-01-01")


def FIXTURE_bar_row(  # noqa: N802 — fixture prefix is the labelling convention
    open_time: datetime, o: float, h: float, lo: float, c: float
) -> dict[str, Any]:
    return {
        "time": int(open_time.timestamp()),
        "open": o,
        "high": h,
        "low": lo,
        "close": c,
        "tick_volume": 100,
        "spread": 35,
        "real_volume": 0,
    }


def FIXTURE_closed_rows() -> list[dict[str, Any]]:  # noqa: N802
    chronological = [
        (10, 2380.00, 2382.50, 2379.00, 2381.00),
        (11, 2381.00, 2384.00, 2380.50, 2383.00),
        (12, 2383.00, 2385.50, 2382.00, 2384.00),
        (13, 2384.00, 2386.00, 2383.50, 2385.00),
        (14, 2385.00, 2387.50, 2384.00, 2386.50),
    ]
    rows = [
        FIXTURE_bar_row(datetime(2026, 1, 6, hour, tzinfo=UTC), o, h, lo, c)
        for hour, o, h, lo, c in chronological
    ]
    forming = FIXTURE_bar_row(datetime(2026, 1, 6, 15, tzinfo=UTC), 2386.50, 2388.00, 2385.50, 2387.00)
    return [forming, *reversed(rows)]


def FIXTURE_tick(moment: datetime) -> dict[str, Any]:  # noqa: N802
    ms = int(moment.timestamp()) * 1000
    return {
        "time": int(moment.timestamp()),
        "bid": 2387.10,
        "ask": 2387.45,
        "last": 0.0,
        "volume": 0,
        "time_msc": ms,
        "flags": 0,
        "volume_real": 0.0,
    }


def FIXTURE_symbol_info(moment: datetime) -> SimpleNamespace:  # noqa: N802
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


class FIXTURE_Terminal:  # noqa: N801 — fixture prefix is the labelling convention
    def __init__(self, now: datetime) -> None:
        self._now = now

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass

    def version(self) -> tuple[int, int, str]:
        return FIXTURE_VERSION

    def last_error(self) -> tuple[int, str]:
        return (0, "ok")

    def copy_rates_from_pos(
        self, symbol: str, timeframe: str, start_pos: int, count: int
    ) -> list[dict[str, Any]] | None:
        return FIXTURE_closed_rows()

    def copy_rates_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]] | None:
        return FIXTURE_closed_rows()

    def symbol_info(self, symbol: str) -> SimpleNamespace | None:
        return FIXTURE_symbol_info(self._now)

    def symbol_info_tick(self, symbol: str) -> dict[str, Any] | None:
        return FIXTURE_tick(self._now)

    def symbols_get(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(name="XAUUSD")]

    def terminal_info(self) -> SimpleNamespace:
        return SimpleNamespace(trade_allowed=False)

    def account_info(self) -> SimpleNamespace:
        return SimpleNamespace(balance=10000.0, currency="USD")


def _adapter(now: datetime) -> Mt5Adapter:
    return Mt5Adapter(
        FIXTURE_Terminal(now),  # type: ignore[arg-type]
        server_timezone="UTC",
        retry_delay_ms=1,
    )


def _as_json(model: MarketBar | MarketQuote | PrecisionRow) -> str:
    return model.model_dump_json()


# -- success side: adapter outputs construct contracts -----------------------


def test_bars_across_quality_paths_construct_and_round_trip() -> None:
    for now in (FIXTURE_NOW, datetime(2026, 1, 6, 18, 0, tzinfo=UTC)):  # fresh, then stale
        result = _adapter(now).get_bars("xauusd", "H1", now_utc=now)
        assert not isinstance(result, AdapterFailure)
        assert len(result) > 0
        for bar in result:
            assert isinstance(bar, MarketBar)
            MarketBar.model_validate_json(_as_json(bar))  # wire round-trip


def test_quote_constructs_and_round_trips() -> None:
    result = _adapter(FIXTURE_NOW).get_latest_quote("xauusd", now_utc=FIXTURE_NOW)
    assert not isinstance(result, AdapterFailure)
    assert isinstance(result, MarketQuote)
    assert result.last is None  # last=0.0 maps to None, never 0.0 as a price
    MarketQuote.model_validate_json(_as_json(result))


def test_spec_constructs_and_round_trips() -> None:
    result = _adapter(FIXTURE_NOW).get_instrument_spec("xauusd", now_utc=FIXTURE_NOW)
    assert not isinstance(result, AdapterFailure)
    assert isinstance(result, PrecisionRow)
    PrecisionRow.model_validate_json(_as_json(result))


# -- rejection side: mutations still fail ------------------------------------


def _valid_bar_dict() -> dict[str, Any]:
    result = _adapter(FIXTURE_NOW).get_bars("xauusd", "H1", now_utc=FIXTURE_NOW)
    assert not isinstance(result, AdapterFailure)
    return json.loads(result[0].model_dump_json())


def _valid_quote_dict() -> dict[str, Any]:
    result = _adapter(FIXTURE_NOW).get_latest_quote("xauusd", now_utc=FIXTURE_NOW)
    assert not isinstance(result, AdapterFailure)
    return json.loads(result.model_dump_json())


def _mutate(base: dict[str, Any], key: str, value: Any, *, drop: bool = False) -> dict[str, Any]:
    mutated = dict(base)
    if drop:
        mutated.pop(key, None)
    else:
        mutated[key] = value
    return mutated


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("wrong-enum", lambda d: _mutate(d, "timeframe", "XX")),
        ("missing-field", lambda d: _mutate(d, "open", None, drop=True)),
        ("null-where-not-nullable", lambda d: _mutate(d, "open", None)),
        ("nan-price", lambda d: _mutate(d, "open", "nan")),
        ("inf-price", lambda d: _mutate(d, "high", "Infinity")),
        ("float-price", lambda d: _mutate(d, "close", 2387.10)),
        ("unknown-extra", lambda d: _mutate(d, "broker_note", "x")),
        ("suffix-instrument", lambda d: _mutate(d, "instrument_id", "XAUUSDm")),
    ],
    ids=[
        "wrong-enum",
        "missing-field",
        "null-where-not-nullable",
        "nan-price",
        "inf-price",
        "float-price",
        "unknown-extra",
        "suffix-instrument",
    ],
)
def test_bar_mutations_fail(label: str, mutate: Any) -> None:
    with pytest.raises(ValidationError):
        MarketBar.model_validate(mutate(_valid_bar_dict()))


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("wrong-enum-quality", lambda d: _mutate(d, "quality_status", "XX")),
        ("missing-field", lambda d: _mutate(d, "bid", None, drop=True)),
        ("spread-without-bid", lambda d: _mutate({**d, "bid": None}, "spread", "0.35")),
        ("nan-price", lambda d: _mutate(d, "ask", "nan")),
        ("float-price", lambda d: _mutate(d, "bid", 2387.10)),
        ("unknown-extra", lambda d: _mutate(d, "broker_note", "x")),
    ],
    ids=[
        "wrong-enum-quality",
        "missing-field",
        "spread-without-bid",
        "nan-price",
        "float-price",
        "unknown-extra",
    ],
)
def test_quote_mutations_fail(label: str, mutate: Any) -> None:
    with pytest.raises(ValidationError):
        MarketQuote.model_validate(mutate(_valid_quote_dict()))


def test_precision_row_mutations_fail() -> None:
    result = _adapter(FIXTURE_NOW).get_instrument_spec("xauusd", now_utc=FIXTURE_NOW)
    assert not isinstance(result, AdapterFailure)
    base = json.loads(result.model_dump_json())
    with pytest.raises(ValidationError):
        PrecisionRow.model_validate(_mutate(base, "decimals", -1))
    with pytest.raises(ValidationError):
        PrecisionRow.model_validate(_mutate(base, "tick_size", None, drop=True))
    with pytest.raises(ValidationError):
        PrecisionRow.model_validate(_mutate(base, "contract_size", "100"))
