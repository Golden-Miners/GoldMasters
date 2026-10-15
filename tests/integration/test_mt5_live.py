"""Live-terminal MT5 verification (operator-run, evidence-recorded).

Status: BLOCKED until the operator runs this on the MT5 host — CI never
claims it (R-10: unrun = BLOCKED, never DONE). The default suite run skips
every test here; the gate never executes them.

Operator runbook
----------------
Prerequisite: a Windows host with the MT5 terminal installed, logged in
with the **investor (read-only) password**, and ``XAUUSD`` enabled in Market
Watch **by hand** (the adapter never calls ``symbol_select`` — D-49).

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
4. Paste the full output into the Phase 2 evidence record. A run whose
   investor assertion fails (``trade_allowed`` True, or master session)
   is a refusal, not a pass — record it as such.

What the tests prove: bare-``initialize()`` attach with no credentials
(D-47), investor read-only session (master rejected, D-46), XAUUSD H1
closed bars + latest tick + instrument spec fetched live with sane
precision. Missing data fails closed to ``INSUFFICIENT_DATA`` — nothing
here invents a price.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from services.mt5_adapter.terminal import Mt5Gateway, TerminalGateway

pytestmark = [
    pytest.mark.live_mt5,
    pytest.mark.skipif(
        os.environ.get("GOLDMASTERS_LIVE_MT5") != "1",
        reason="operator-run only: needs a live MT5 terminal (R-10 unrun = BLOCKED)",
    ),
]

REQUIRES_LIVE_GATE = "GOLDMASTERS_LIVE_MT5=1"


def _gateway() -> TerminalGateway:
    """Live gateway (module import is safe: the package loads lazily)."""
    return Mt5Gateway()


def test_live_bare_attach_is_read_only() -> None:
    """Bare initialize attaches; the session must be investor read-only."""
    from services.mt5_adapter.adapter import Mt5Adapter

    gateway = _gateway()
    assert gateway.initialize() is True
    try:
        terminal = gateway.terminal_info()
        account = gateway.account_info()
        assert terminal is not None and account is not None
        assert bool(terminal.trade_allowed) is False, "master session refused (D-46)"
        print(f"\nlive attach ok: trade_allowed={terminal.trade_allowed}")
    finally:
        gateway.shutdown()
    adapter = Mt5Adapter(gateway, server_timezone="UTC")
    assert adapter.capabilities()["provider_id"] == "mt5"


def test_live_xauusd_h1_bars_tick_and_spec() -> None:
    """XAUUSD H1 bars + tick + spec with sanity output for the evidence record."""
    from services.mt5_adapter.adapter import AdapterFailure, Mt5Adapter

    now = datetime.now(UTC)
    adapter = Mt5Adapter(_gateway(), server_timezone="UTC")
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
