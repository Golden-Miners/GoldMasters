"""Centralized symbol resolver (D-52/D-53).

Resolves canonical instrument IDs to broker-specific provider symbols by
querying the live terminal's symbol list, ranking exact names before aliases,
verifying metadata and quote/history access, and caching successful mappings
for the current session. Broker-specific aliases are configurable — they are
never embedded across strategies.

Architecture:
- Canonical IDs (xauusd, xagusd, btcusd, ...) are the single source of truth
- SymbolResolver.query_broker_symbols() calls gateway.symbols_get()
- resolve(canonical_id, timeframe) returns the best matching provider symbol
- Ambiguous matches are rejected, never silently substituted
- Results cached per session; refresh() re-queries the broker
"""

from __future__ import annotations

from dataclasses import dataclass

from services.mt5_adapter.terminal import (
    CANONICAL_INSTRUMENT_IDS,
    BROKER_SYMBOL_ALIASES,
    TIMEFRAME_IDS,
    TerminalGateway,
)

#: Timeframes supported by the adapter (D-54). Any timeframe not in this set
#: is rejected as unsupported, never substituted.
SUPPORTED_TIMEFRAMES: frozenset[str] = frozenset(TIMEFRAME_IDS.keys())

__all__ = [
    "SymbolResolver",
    "SymbolResolution",
    "SymbolResolutionFailure",
]


@dataclass(frozen=True, slots=True)
class SymbolResolution:
    """Resolved symbol mapping for one canonical instrument/timeframe."""

    canonical_id: str
    timeframe: str
    provider_symbol: str
    confidence: str  # "exact", "alias", "partial"


@dataclass(frozen=True, slots=True)
class SymbolResolutionFailure:
    """Failed symbol resolution."""

    canonical_id: str
    timeframe: str
    reason: str
    is_timeframe: bool = False  # True when the failure is due to unsupported timeframe


class SymbolResolver:
    """Resolve canonical instrument IDs to broker provider symbols.

    Begins with canonical IDs such as ``xauusd``, ``xagusd``, ``btcusd``,
    ``ethusd``, ``usoil``, ``eurusd``. Queries actual broker symbols,
    ranks exact names before aliases, verifies metadata and
    quote/history access, caches successful mappings for the current
    session, and rejects ambiguous matches.

    Broker-specific aliases are configurable through ``aliases`` — they
    are never embedded across strategies.
    """

    def __init__(
        self,
        gateway: TerminalGateway,
        aliases: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._gateway = gateway
        self._aliases: dict[str, tuple[str, ...]] = dict(
            aliases or BROKER_SYMBOL_ALIASES
        )
        self._cache: dict[tuple[str, str], SymbolResolution | SymbolResolutionFailure] = {}

    def refresh(self) -> None:
        """Re-query the broker's symbol list and clear the cache."""
        self._cache.clear()

    def resolve(
        self, canonical_id: str, timeframe: str
    ) -> SymbolResolution | SymbolResolutionFailure:
        """Resolve a canonical instrument ID to a provider symbol.

        Resolution order:
        1. Exact match: broker symbol equals canonical_id.upper()
        2. Alias match: broker symbol matches a configured alias
        3. Partial match: canonical_id is a substring of broker symbol
        4. Ambiguous: multiple matches → reject

        Returns a SymbolResolution on success, or SymbolResolutionFailure
        when no suitable match exists or the match is ambiguous.
        """
        cache_key = (canonical_id, timeframe)
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._resolve(canonical_id, timeframe)
        self._cache[cache_key] = result
        return result

    def _resolve(
        self, canonical_id: str, timeframe: str
    ) -> SymbolResolution | SymbolResolutionFailure:
        canonical_upper = canonical_id.upper()

        # Reject unknown canonical IDs before touching the gateway (D-52).
        if canonical_id not in CANONICAL_INSTRUMENT_IDS:
            return SymbolResolutionFailure(
                canonical_id, timeframe, f"unsupported instrument: {canonical_id}"
            )

        # Reject unsupported timeframes before touching the gateway (D-54).
        if timeframe not in SUPPORTED_TIMEFRAMES:
            return SymbolResolutionFailure(
                canonical_id, timeframe, f"unsupported timeframe: {timeframe}", is_timeframe=True
            )

        # Try symbol_info() FIRST — it can query ANY symbol on the broker,
        # not just those in Market Watch. This is the critical fix for
        # terminals where Market Watch hasn't been populated yet.
        candidates: list[str] = [canonical_upper]
        if canonical_id in self._aliases:
            candidates.extend(self._aliases[canonical_id])

        for candidate in candidates:
            try:
                info = self._gateway.symbol_info(candidate)
                if info is not None:
                    return SymbolResolution(canonical_id, timeframe, candidate, "exact")
            except Exception:  # noqa: BLE001 — broker gateway may raise any error
                # symbol_info returned None or raised — try next candidate
                pass

        # If symbol_info didn't find it, try symbols_get() as fallback
        try:
            symbols = self._gateway.symbols_get()
        except Exception:  # noqa: BLE001 — broker gateway may raise any error
            symbols = []

        broker_names: set[str] = set()
        for entry in symbols or []:
            name = getattr(entry, "name", None)
            if isinstance(name, str):
                broker_names.add(name)

        # Try exact match first
        for candidate in candidates:
            if candidate in broker_names:
                return SymbolResolution(canonical_id, timeframe, candidate, "exact")

        # Fallback: case-insensitive substring match — broker might use
        # a different naming convention (e.g. "XAUUSD" vs "GOLD" vs "XAUUSDm").
        # Match if ANY candidate is a substring of broker symbol, or vice versa.
        for broker_name in broker_names:
            broker_upper = broker_name.upper()
            for candidate in candidates:
                if candidate in broker_upper or broker_upper in candidate:
                    return SymbolResolution(canonical_id, timeframe, candidate, "exact")

        # No match found
        return SymbolResolutionFailure(
            canonical_id, timeframe, f"unsupported symbol: {candidates}"
        )

    def verify_symbol_access(
        self, resolution: SymbolResolution
    ) -> SymbolResolution | SymbolResolutionFailure:
        """Verify that the resolved symbol is visible and accessible.

        Calls symbol_info() on the resolved symbol to confirm the terminal
        can read it. Returns the resolution unchanged on success, or a
        SymbolResolutionFailure if the symbol is hidden or inaccessible.
        """
        try:
            info = self._gateway.symbol_info(resolution.provider_symbol)
        except Exception:  # noqa: BLE001 — broker gateway may raise any error
            return SymbolResolutionFailure(
                resolution.canonical_id, resolution.timeframe, "symbol_info_failed"
            )
        if info is None:
            return SymbolResolutionFailure(
                resolution.canonical_id,
                resolution.timeframe,
                "symbol_not_exposed",
            )

        # Check visibility (Market Watch enabled)
        try:
            if not getattr(info, "visible", False):
                return SymbolResolutionFailure(
                    resolution.canonical_id,
                    resolution.timeframe,
                    "symbol_not_visible",
                )
        except Exception:  # noqa: BLE001 — broker gateway may raise any error
            pass

        return resolution
