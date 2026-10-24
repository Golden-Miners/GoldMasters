"""Live-terminal MT5 verification (operator-run, evidence-recorded).

Status: BLOCKED until the operator runs this on the MT5 host — CI never
claims it (R-10: unrun = BLOCKED, never DONE). The default suite run skips
every test here; the gate never executes them.

Operator runbook
----------------
Prerequisite: a Windows host with the MT5 terminal installed, logged in
with any account mode (investor/master/demo/live — GoldMasters is
signals-only and never places orders, so any session mode is acceptable),
and the desired symbol enabled in Market Watch **by hand** (the adapter
never calls ``symbol_select`` — D-49).

1. Install the package in a Python 3.10+ environment. Risk: the
   ``MetaTrader5`` wheel is Windows-only and per-Python-version; on
   3.14 it may have no compatible build — fall back to a 3.12 venv
   (02-RESEARCH.md §7 risk 1): ``pip install MetaTrader5``.
2. From the repo root run::

       set GOLDMASTERS_LIVE_MT5=1
       uv run pytest tests/integration/test_mt5_live.py -m live_mt5 -s

   (PowerShell: ``$env:GOLDMASTERS_LIVE_MT5 = "1"``.)
3. Confirm the printed sanity lines: closed-bar count, last close time,
   bid/ask, digits/point/build.
4. Paste the full output into the Phase 2 evidence record.

What the tests prove: bare-``initialize()`` attach with no credentials
(D-47), any MT5 session mode accepted (investor/master/demo/live —
signals-only boundary enforced by absence of order-execution capability,
not by account mode), XAUUSD H1 closed bars + latest tick + instrument
spec fetched live with sane precision. Missing data fails closed to
``INSUFFICIENT_DATA`` — nothing here invents a price.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from services.mt5_adapter.adapter import AdapterFailure, Mt5Adapter
from services.mt5_adapter.symbol_resolver import SymbolResolver
from services.mt5_adapter.terminal import Mt5Gateway, TerminalManager

pytestmark = [
    pytest.mark.live_mt5,
    pytest.mark.skipif(
        os.environ.get("GOLDMASTERS_LIVE_MT5") != "1",
        reason="operator-run only: needs a live MT5 terminal (R-10 unrun = BLOCKED)",
    ),
]

REQUIRES_LIVE_GATE = "GOLDMASTERS_LIVE_MT5=1"


def _terminal_manager() -> TerminalManager:
    """Live terminal manager (module import is safe: the package loads lazily)."""
    return TerminalManager(Mt5Gateway())


def _symbol_resolver(gateway: Mt5Gateway) -> SymbolResolver:
    """Live symbol resolver."""
    return SymbolResolver(gateway)


def test_live_bare_attach_any_session_mode() -> None:
    """Bare initialize attaches; any MT5 session mode accepted.

    GoldMasters is signals-only: it never places or modifies orders,
    so any MT5 session mode (investor/master/demo/live) is acceptable
    for reading market data.
    """
    tm = _terminal_manager()
    assert tm.start() is True
    try:
        terminal = tm._gateway.terminal_info()
        account = tm._gateway.account_info()
        assert terminal is not None and account is not None
        print(f"\nlive attach ok: trade_allowed={terminal.trade_allowed}")
    finally:
        tm.stop()
    gateway = Mt5Gateway()
    gateway.initialize()
    try:
        resolver = SymbolResolver(gateway)
        adapter = Mt5Adapter(TerminalManager(gateway), resolver, server_timezone="UTC")
        caps = adapter.capabilities()
        assert caps["provider_id"] == "mt5"
    finally:
        gateway.shutdown()


def test_live_xauusd_h1_bars_tick_and_spec() -> None:
    """XAUUSD H1 bars + tick + spec with sanity output for the evidence record."""
    now = datetime.now(UTC)
    gateway = Mt5Gateway()
    gateway.initialize()
    try:
        resolver = SymbolResolver(gateway)
        tm = TerminalManager(gateway)
        tm._initialized = True  # Already initialized above
        adapter = Mt5Adapter(tm, resolver, server_timezone="UTC")
        bars = adapter.get_bars("xauusd", "H1", now_utc=now)
        assert not isinstance(bars, AdapterFailure), f"bars failed: {bars}"
        quote = adapter.get_latest_quote("xauusd", now_utc=now)
        assert not isinstance(quote, AdapterFailure), f"quote failed: {quote}"
        spec = adapter.get_instrument_spec("xauusd", now_utc=now)
        assert not isinstance(spec, AdapterFailure), f"spec failed: {spec}"
        last = bars[-1]
        print(f"\nlive bars: count={len(bars)} last_close={last.bar_close_time}")
        print(f"live tick: bid={quote.bid} ask={quote.ask} last={quote.last}")
        print(
            f"live spec: decimals={spec.decimals} tick_size={spec.tick_size} "
            f"provenance={spec.provider_spec_version}"
        )
    finally:
        gateway.shutdown()