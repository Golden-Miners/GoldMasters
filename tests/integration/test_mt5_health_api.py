"""MT5 tracer API tests: FakeTerminal-backed app proves the slice end to end.

Covers 02-01 Task 3 behaviors 4-6: bars/quote endpoints return contract
JSON, /health carries the seven-key provider object, unsupported selection
fails visibly with no fallback call, and no FIXTURE_ symbol leaks into
production paths. All rows are generated at call time (anchored to the
current hour) — never live data, never committed market history.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from goldmasters_api.app import create_app


@pytest.fixture(autouse=True)
def _database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Required key since 01-10: point the suite at an unreachable localhost DB."""
    monkeypatch.setenv(
        "GOLDMASTERS_DATABASE_URL",
        "postgresql+psycopg://127.0.0.1:5432/goldmasters",
    )


def _live_rows(count: int) -> list[dict[str, Any]]:
    """Terminal-order rows anchored to now: forming bar first, then closed newest-first."""
    hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    base = 2380.00
    rows: list[dict[str, Any]] = [
        {
            "time": int(hour.timestamp()),
            "open": base + count * 1.0,
            "high": base + count * 1.0 + 1.5,
            "low": base + count * 1.0 - 1.0,
            "close": base + count * 1.0 + 0.5,
            "tick_volume": 140,
            "spread": 35,
            "real_volume": 0,
        }
    ]
    for back in range(1, count + 1):
        opened = hour - timedelta(hours=back)
        price = base + (count - back) * 1.0
        rows.append(
            {
                "time": int(opened.timestamp()),
                "open": price,
                "high": price + 2.5,
                "low": price - 1.0,
                "close": price + 1.0,
                "tick_volume": 100 + back,
                "spread": 35,
                "real_volume": 0,
            }
        )
    return rows


class _LiveFakeTerminal:
    """Gateway double with now-anchored rows; records every call."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def initialize(self) -> bool:
        self.calls.append("initialize")
        return True

    def shutdown(self) -> None:
        self.calls.append("shutdown")

    def version(self) -> tuple[int, int, str]:
        self.calls.append("version")
        return (500, 4570, "2026-01-01")

    def last_error(self) -> tuple[int, str]:
        self.calls.append("last_error")
        return (0, "ok")

    def copy_rates_from_pos(
        self, symbol: str, timeframe: str, start_pos: int, count: int
    ) -> list[dict[str, Any]] | None:
        self.calls.append(f"copy_rates_from_pos:{symbol}:{timeframe}")
        return _live_rows(count - 1)

    def copy_rates_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]] | None:
        self.calls.append("copy_rates_range")
        return _live_rows(3)

    def symbol_info_tick(self, symbol: str) -> dict[str, Any] | None:
        self.calls.append(f"symbol_info_tick:{symbol}")
        now = int(datetime.now(UTC).timestamp())
        return {
            "time": now,
            "bid": 2387.10,
            "ask": 2387.45,
            "last": 0.0,
            "volume": 0,
            "time_msc": now * 1000,
            "flags": 0,
            "volume_real": 0.0,
        }

    def symbol_info(self, symbol: str) -> SimpleNamespace | None:
        self.calls.append(f"symbol_info:{symbol}")
        return SimpleNamespace(
            digits=2,
            point=0.01,
            trade_tick_size=0.01,
            trade_tick_value=1.0,
            trade_contract_size=100.0,
            visible=True,
            time=int(datetime.now(UTC).timestamp()),
            bid=2387.10,
            ask=2387.45,
        )

    def symbols_get(self) -> list[SimpleNamespace]:
        self.calls.append("symbols_get")
        return [SimpleNamespace(name="XAUUSD")]

    def terminal_info(self) -> SimpleNamespace:
        self.calls.append("terminal_info")
        return SimpleNamespace(trade_allowed=False)

    def account_info(self) -> SimpleNamespace:
        self.calls.append("account_info")
        return SimpleNamespace(balance=10000.0, currency="USD")


def _client() -> TestClient:
    return TestClient(create_app(gateway=_LiveFakeTerminal()))


def test_bars_endpoint_returns_contract_bars() -> None:
    with _client() as client:
        response = client.get("/v1/market/bars?instrument_id=xauusd&timeframe=H1")
    assert response.status_code == 200, response.text
    bars = response.json()
    assert len(bars) == 10
    first = bars[0]
    assert first["provider_id"] == "mt5"
    assert first["provider_symbol"] == "XAUUSD"
    assert first["instrument_id"] == "xauusd"
    assert first["timeframe"] == "H1"
    assert first["quality_status"] == "ok"
    assert first["volume_type"] == "tick"


def test_quote_endpoint_returns_tick_quote_with_null_last() -> None:
    with _client() as client:
        response = client.get("/v1/market/quote?instrument_id=xauusd")
    assert response.status_code == 200, response.text
    quote = response.json()
    assert quote["provider_id"] == "mt5"
    assert quote["bid"] == "2387.1"
    assert quote["ask"] == "2387.45"
    assert quote["last"] is None
    assert quote["quality_status"] == "ok"


def test_health_carries_seven_key_provider_object() -> None:
    with _client() as client:
        body = client.get("/health").json()
    provider = body["provider"]
    assert set(provider) == {
        "provider_id",
        "status",
        "market_open",
        "terminal_build",
        "last_bar_close_time",
        "last_quote_time",
        "checked_at",
    }
    assert provider["provider_id"] == "mt5"
    assert provider["status"] == "connected"


def test_unsupported_selection_fails_visibly_without_fallback() -> None:
    gateway = _LiveFakeTerminal()
    with TestClient(create_app(gateway=gateway)) as client:
        bars = client.get("/v1/market/bars?instrument_id=silver&timeframe=H1")
        quote = client.get("/v1/market/quote?instrument_id=xauusd")
        bad_timeframe = client.get("/v1/market/bars?instrument_id=xauusd&timeframe=M15")
    assert bars.status_code == 400
    assert "UNSUPPORTED_INSTRUMENT" in bars.text
    assert bad_timeframe.status_code == 400
    assert "UNSUPPORTED_TIMEFRAME" in bad_timeframe.text
    assert quote.status_code == 200
    assert not any(call.startswith("copy_rates_from_pos:silver") for call in gateway.calls)


def test_no_fixture_symbol_leaks_into_production_paths() -> None:
    repo = Path(__file__).resolve().parents[2]
    offenders = []
    for root in ("services", "apps", "packages"):
        for path in (repo / root).rglob("*.py"):
            if "FIXTURE_" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(repo)))
    assert offenders == []
