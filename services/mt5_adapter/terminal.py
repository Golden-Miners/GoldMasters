"""MT5 terminal gateway — the single module that reaches MetaTrader5 (D-44/D-47).

Every ``MetaTrader5`` reference is confined here and resolved lazily through
:func:`load_mt5` (``importlib`` inside the function body), so importing this
module — and the adapter above it — never requires the package to be
installed. Tests inject a :class:`TerminalGateway` double; CI never installs
the wheel (02-RESEARCH.md §6 seam).

Attach pattern: bare ``initialize()`` with no arguments, against the
already-running terminal the operator attached by hand. This module never
handles secrets and never changes terminal state: symbol visibility is read,
never granted — the operator enables Market Watch entries by hand (D-49).
"""

from __future__ import annotations

import importlib
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "H1_TIMEFRAME_ID",
    "TIMEFRAME_IDS",
    "Mt5Gateway",
    "TerminalGateway",
    "load_mt5",
]

#: MT5 H1 period id from the documented timeframe table
#: (https://www.mql5.com/en/docs/constants/chartconstants/enum_timeframes).
H1_TIMEFRAME_ID = 16385

#: Provider-timeframe token → MT5 period id. Only H1 is mapped: the adapter
#: reports every other timeframe unsupported (D-54), so no other id ships.
TIMEFRAME_IDS: dict[str, int] = {"H1": H1_TIMEFRAME_ID}

#: ``symbol_info_tick`` tuple field order per the documented integration page
#: (https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfotick_py) —
#: must-verify-first against the installed package (RISK-03); used only when
#: the payload has no ``_asdict`` mapping.
_TICK_FIELDS: tuple[str, ...] = (
    "time",
    "bid",
    "ask",
    "last",
    "volume",
    "time_msc",
    "flags",
    "volume_real",
)


@runtime_checkable
class TerminalGateway(Protocol):
    """Narrow read-only surface the adapter codes against (02-RESEARCH.md §1)."""

    def initialize(self) -> bool:
        """Attach to the running terminal (bare form, no arguments)."""
        ...

    def shutdown(self) -> None:
        """Close the IPC connection (the terminal itself keeps running)."""
        ...

    def version(self) -> Any:
        """Terminal version triple; the build feeds precision provenance."""
        ...

    def last_error(self) -> Any:
        """Most recent ``(code, description)`` tuple after a ``None`` return."""
        ...

    def copy_rates_from_pos(
        self, symbol: str, timeframe: str, start_pos: int, count: int
    ) -> list[dict[str, Any]] | None:
        """Closed-bar window; ``start_pos=0`` is the still-forming bar."""
        ...

    def copy_rates_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]] | None:
        """Datetime-window backfill for gap re-checks (plan 02-02 hot path: no)."""
        ...

    def symbol_info(self, symbol: str) -> Any | None:
        """Instrument descriptor, or ``None`` when the terminal hides it."""
        ...

    def symbol_info_tick(self, symbol: str) -> dict[str, Any] | None:
        """Latest tick mapping, or ``None`` on error."""
        ...

    def symbols_get(self) -> list[Any] | None:
        """Visible symbol list for capability reporting, never substitution."""
        ...

    def terminal_info(self) -> Any | None:
        """Terminal descriptor carrying the read-only session flag."""
        ...

    def account_info(self) -> Any | None:
        """Account descriptor; presence-checked, never stored."""
        ...


def load_mt5() -> Any:
    """Import the MetaTrader5 package lazily (collection never requires it)."""
    return importlib.import_module("MetaTrader5")


class Mt5Gateway:
    """Live :class:`TerminalGateway` over the operator's terminal (D-45/D-47)."""

    def initialize(self) -> bool:
        return bool(load_mt5().initialize())

    def shutdown(self) -> None:
        load_mt5().shutdown()

    def version(self) -> Any:
        return load_mt5().version()

    def last_error(self) -> Any:
        return load_mt5().last_error()

    def copy_rates_from_pos(
        self, symbol: str, timeframe: str, start_pos: int, count: int
    ) -> list[dict[str, Any]] | None:
        rows = load_mt5().copy_rates_from_pos(symbol, TIMEFRAME_IDS[timeframe], start_pos, count)
        if rows is None:
            return None
        names = rows.dtype.names
        if not names:
            return None
        return [dict(zip(names, (row[name] for name in names), strict=True)) for row in rows]

    def copy_rates_range(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]] | None:
        rows = load_mt5().copy_rates_range(symbol, TIMEFRAME_IDS[timeframe], start, end)
        if rows is None:
            return None
        names = rows.dtype.names
        if not names:
            return None
        return [dict(zip(names, (row[name] for name in names), strict=True)) for row in rows]

    def symbol_info(self, symbol: str) -> Any | None:
        return load_mt5().symbol_info(symbol)

    def symbol_info_tick(self, symbol: str) -> dict[str, Any] | None:
        tick = load_mt5().symbol_info_tick(symbol)
        if tick is None:
            return None
        as_dict = getattr(tick, "_asdict", None)
        if callable(as_dict):
            return dict(as_dict())
        return dict(zip(_TICK_FIELDS, tuple(tick), strict=False))

    def symbols_get(self) -> list[Any] | None:
        symbols = load_mt5().symbols_get()
        return None if symbols is None else list(symbols)

    def terminal_info(self) -> Any | None:
        return load_mt5().terminal_info()

    def account_info(self) -> Any | None:
        return load_mt5().account_info()


#: Canonical instrument IDs that GoldMasters supports (D-52/D-53).
#: Broker-specific symbols are resolved at runtime through SymbolResolver.
CANONICAL_INSTRUMENT_IDS: tuple[str, ...] = (
    "xauusd",
    "xagusd",
    "btcusd",
    "ethusd",
    "usoil",
    "eurusd",
)

#: Broker-specific symbol aliases per canonical ID (D-52).
#: First entry is preferred; later entries are fallbacks. Override via config.
BROKER_SYMBOL_ALIASES: dict[str, tuple[str, ...]] = {
    "xauusd": (
        "GOLD.i#", "XAUUSD", "XAUUSDm", "GOLD",
        "XAUUSD.m", "GOLD.m", "XAUUSD.ecn", "GOLD.ecn",
        "XAUUSD.raw", "GOLD.raw", "XAUUSD.std", "GOLD.std",
        "XAUUSD.pro", "GOLD.pro", "XAUUSD.zero", "GOLD.zero",
        "xauusd", "gold", "XAUUSD.c", "GOLD.c",
        "XAUUSD.s", "GOLD.s", "XAUUSD.f", "GOLD.f",
        "XAUUSD.z", "GOLD.z",
        "XAUUSD.k", "GOLD.k", "XAUUSD.n", "GOLD.n",
        "XAUUSD.q", "GOLD.q", "XAUUSD.r", "GOLD.r",
        "XAUUSD.t", "GOLD.t", "XAUUSD.u", "GOLD.u",
        "XAUUSD.v", "GOLD.v", "XAUUSD.w", "GOLD.w",
        "XAUUSD.x", "GOLD.x", "XAUUSD.y", "GOLD.y",
        "XAUUSD.i", "GOLD.i", "XAUUSD#", "GOLD#",
        "XAUUSD+", "GOLD+", "XAUUSD+ ", "GOLD+ ",
        "XAUUSD .c", "GOLD .c", "XAUUSD .s", "GOLD .s",
        "XAUUSD.i#", "GOLD.i#",
        "XAUUSD.m#", "GOLD.m#",
        "XAUUSD.ecn#", "GOLD.ecn#",
        "XAUUSD.raw#", "GOLD.raw#",
        "XAUUSD.std#", "GOLD.std#",
        "XAUUSD.pro#", "GOLD.pro#",
        "XAUUSD.zero#", "GOLD.zero#",
        "xauusd.i#", "gold.i#",
        "XAUUSD.c.i#", "GOLD.c.i#",
        "XAUUSD.s.i#", "GOLD.s.i#",
        "XAUUSD.f.i#", "GOLD.f.i#",
        "XAUUSD.z.i#", "GOLD.z.i#",
    ),
    "xagusd": ("SILVER.i#", "XAGUSD", "XAGUSDm", "SILVER"),
    "btcusd": ("BTC.i#", "BTCUSD", "BTCUSDm", "BTC"),
    "ethusd": ("ETH.i#", "ETHUSD", "ETHUSDm", "ETH"),
    "usoil": ("OIL.i#", "USOIL", "USOILm", "OIL"),
    "eurusd": ("EUR.i#", "EURUSD", "EURUSDm", "EUR"),
}


class TerminalManager:
    """Persistent MT5 terminal connection manager.

    Owns the initialize/shutdown lifecycle so individual reads don't
    create/destroy IPC connections. Can optionally launch the terminal
    from a configured executable path (never terminates user-owned
    terminals — only closes the IPC connection on stop()).
    """

    def __init__(
        self,
        gateway: TerminalGateway,
        terminal_path: str | None = None,
        startup_timeout_seconds: float = 10.0,
    ) -> None:
        self._gateway = gateway
        self._terminal_path = terminal_path
        self._startup_timeout_seconds = startup_timeout_seconds
        self._initialized = False

    def start(self) -> bool:
        """Attach to a running terminal, optionally launching it first.

        Returns True when the IPC connection is established and ready
        for reads. Returns False if the terminal is unreachable after
        the bounded timeout.
        """
        import threading

        result = {"initialized": False}

        def _try_initialize() -> None:
            try:
                if self._gateway.initialize():
                    result["initialized"] = True
            except Exception:  # noqa: BLE001 — terminal.initialize() may raise any error
                result["initialized"] = False

        # Run initialize() in a thread with a timeout so a black-holed
        # terminal can't block API startup indefinitely.
        t = threading.Thread(target=_try_initialize, daemon=True)
        t.start()
        t.join(timeout=self._startup_timeout_seconds)

        if result["initialized"]:
            self._initialized = True
            return True

        # If direct initialize failed and we have a terminal path,
        # try launching the terminal first, then attaching.
        if self._terminal_path:
            import subprocess

            try:
                subprocess.Popen([self._terminal_path])
            except (OSError, FileNotFoundError):
                return False

            deadline = __import__("time").time() + self._startup_timeout_seconds
            while __import__("time").time() < deadline:
                t = threading.Thread(target=_try_initialize, daemon=True)
                t.start()
                t.join(timeout=2.0)
                if result["initialized"]:
                    self._initialized = True
                    return True
                __import__("time").sleep(0.5)

        return False

    def stop(self) -> None:
        """Close the IPC connection (terminal process keeps running)."""
        if self._initialized:
            self._gateway.shutdown()
            self._initialized = False

    def is_ready(self) -> bool:
        """True when the terminal is attached and ready for reads."""
        return self._initialized

    def __enter__(self) -> TerminalManager:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()


__all__.extend(["TerminalManager", "CANONICAL_INSTRUMENT_IDS", "BROKER_SYMBOL_ALIASES"])
